import os
import json
import time
import streamlit as st
import pandas as pd
from google import genai
# Import types and specific classes (Part, Content) for the chat fix
from google.genai import types
from google.genai.types import Part, Content 


# --- Configuration and Setup ---

# IMPORTANT: Using the provided key as a fallback. Replace with your actual key or use environment variable
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAfX5tJn6tg1323-uXUZke6-G96_1uYp4s")
MAX_RETRIES = 5
INITIAL_DELAY = 1

# Initialize Gemini Client (outside the main loop for efficiency)
try:
    if API_KEY:
        GEMINI_CLIENT = genai.Client(api_key=API_KEY)
    else:
        GEMINI_CLIENT = None
except Exception as e:
    st.warning(f"Error initializing Gemini client: {e}. AI features will be disabled.")
    GEMINI_CLIENT = None

# --- Structured Output Schema for the Itinerary ---
ITINERARY_SCHEMA = types.Schema(
    type=types.Type.ARRAY,
    description="A list of daily itinerary plans.",
    items=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "day": types.Schema(type=types.Type.INTEGER, description="The day number, starting from 1."),
            "theme": types.Schema(type=types.Type.STRING, description="A short, catchy theme for the day (e.g., 'Historical Walking Tour', 'Cheap Eats Day')."),
            "plan": types.Schema(
                type=types.Type.ARRAY,
                description="List of activities for the day.",
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "time": types.Schema(type=types.Type.STRING, description="Time slot (e.g., 'Morning', 'Lunch', 'Afternoon', 'Evening')."),
                        "activity": types.Schema(type=types.Type.STRING, description="The specific activity or location."),
                        "estimated_cost_inr": types.Schema(type=types.Type.NUMBER, description="Estimated cost for the activity in Indian Rupee (INR) (use 0 for free activities).")
                    },
                    required=["time", "activity", "estimated_cost_inr"]
                )
            ),
            "efficiency_tip": types.Schema(type=types.Type.STRING, description="A practical, budget-focused tip for minimizing travel time or cost, focusing on walking/public transport.")
        },
        required=["day", "theme", "plan", "efficiency_tip"]
    )
)

# --- Core Functionality: AI Generation (Itinerary) ---

def generate_student_itinerary(destination, days, interests):
    """Connects to the Gemini API to generate a structured, budget-friendly itinerary."""
    if not GEMINI_CLIENT:
        return "Error: Gemini client is not initialized. Check API Key.", None
        
    system_instruction = (
        "You are a World-Class Budget Student Travel Expert and Route Planner. "
        "Your goal is to create a detailed, efficient, and fun travel plan for a student with limited funds. "
        "All suggestions MUST prioritize free or low-cost activities (under ₹500 INR). "
        "You must return the response as a valid JSON object matching the provided schema. "
        "Provide specific cost estimates for each activity in **Indian Rupee (INR)**. "
        "For the 'efficiency_tip', focus on grouping nearby locations to minimize travel or suggesting budget public transport passes."
    )

    user_query = (
        f"Generate a {days}-day travel itinerary for a trip to {destination}. "
        f"The total budget is restricted (focus on lowest costs). "
        f"The student is interested in: {interests}. "
        "Ensure the plan is efficient to follow, grouping activities by location."
    )

    generation_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=ITINERARY_SCHEMA,
    )

    last_error = "Unknown error occurred before first API call."
    
    for attempt in range(MAX_RETRIES):
        try:
            response = GEMINI_CLIENT.models.generate_content(
                model='gemini-2.5-flash',
                contents=[user_query],
                config=generation_config,
            )

            try:
                itinerary_json = json.loads(response.text)
                return "Itinerary generated successfully!", itinerary_json
            except json.JSONDecodeError as e:
                last_error = f"AI response format error (Attempt {attempt+1}): Failed to parse JSON response. Details: {e}"
                
        except Exception as e:
            last_error = f"Gemini API connection error (Attempt {attempt+1}): {e}"

        if attempt < MAX_RETRIES - 1:
            delay = INITIAL_DELAY * (2 ** attempt)
            time.sleep(delay)

    return f"Failed to generate itinerary after multiple retries. Last known error: {last_error}", None


# --- Display Utility (Itinerary) ---

def display_itinerary_streamlit(itinerary):
    """Renders the structured itinerary using Streamlit components."""
    if not itinerary:
        return

    total_cost = sum(
        sum(activity.get("estimated_cost_inr", 0) for activity in day_plan.get("plan", []))
        for day_plan in itinerary
    )

    st.subheader("✨ Your Generated Itinerary")
    st.markdown(f"**Total Estimated Activity Cost:** **₹{total_cost:,.0f}**")
    st.markdown("_Note: This excludes flights, accommodation, and general food._")

    for day_plan in itinerary:
        day_num = day_plan.get("day", "N/A")
        theme = day_plan.get("theme", "No Theme")
        plan = day_plan.get("plan", [])
        tip = day_plan.get("efficiency_tip", "No tip provided.")

        daily_cost = sum(activity.get("estimated_cost_inr", 0) for activity in plan)

        with st.expander(f"📅 Day {day_num}: {theme} (Cost: ₹{daily_cost:,.0f})", expanded=False):
            
            activities_data = [
                {
                    "Time": activity.get("time", "N/A"),
                    "Activity": activity.get("activity", "N/A"),
                    "Cost (INR)": f"₹{activity.get('estimated_cost_inr', 0):,.0f}"
                }
                for activity in plan
            ]
            st.dataframe(activities_data, use_container_width=True, hide_index=True)

            st.info(f"**🚌 Efficiency Tip:** {tip}")

# --- Utility Function for Maps/Weather ---

def get_coords(city_country):
    """Simple function to get placeholder coordinates based on destination name."""
    if "goa" in city_country.lower():
        return 15.3004, 74.0855 # Goa
    if "delhi" in city_country.lower():
        return 28.7041, 77.1025 # Delhi
    if "pondicherry" in city_country.lower() or "puducherry" in city_country.lower():
        return 11.9416, 79.8083 # Pondicherry
    if "kathmandu" in city_country.lower():
        return 27.7172, 85.3240 # Kathmandu
    if "usa" in city_country.lower():
        return 39.8283, -98.5795 # Center of the USA
    return 30.0, 70.0 # Default center

def render_trip_tools(destination):
    """Renders functional maps and realistic weather placeholders (Budget Charts removed)."""
    st.markdown("---")
    st.subheader(f"🗺️ Tools & Info for {destination}")
    
    # Using 2 columns for layout since Budget Charts are removed
    col1, col2 = st.columns(2)
    
    # 1. Interactive Map
    with col1:
        st.info("📍 **Interactive Map**")
        lat, lon = get_coords(destination)
        
        # Use a DataFrame for st.map
        map_data = pd.DataFrame({"lat": [lat], "lon": [lon]})
        st.map(map_data, zoom=10)
        st.markdown(f"**Tip:** This map centers on the approximate location of {destination}.")

    # 2. Weather Forecast
    with col2:
        st.info("☀️ **Weather Forecast**")
        st.markdown(f"**Estimated Current Weather in {destination}:**")
        # Placeholder data for weather report visualization
        st.metric("Temperature", "28°C", "-2°C (Cooler than yesterday)")
        st.metric("Condition", "Partly Cloudy", "High Chance of Rain Tomorrow")
        st.markdown("*To implement a real report, integrate a weather API (e.g., OpenWeatherMap).*")


# --- Page 1: Plan Trip & Itinerary Display ---

def render_plan_trip_page():
    """Renders the main form and dynamic itinerary results."""
    
    st.markdown("---")

    # Initialize session state for the form inputs
    if 'destination' not in st.session_state:
        st.session_state.destination = ""
        st.session_state.days = 3
        st.session_state.interests = ""
        st.session_state.itinerary_data = None 

    # User Input Form
    with st.form("travel_form"):
        st.subheader("Enter Trip Details")
        
        destination = st.text_input("Destination (City, Country)", 
                                    value=st.session_state.destination,
                                    help="E.g., Delhi, India", 
                                    key="destination_input")
        days = st.number_input("Number of Days", 
                                min_value=1, max_value=14, 
                                value=st.session_state.days, 
                                key="days_input")
        interests = st.text_area("Main Interests", 
                                 value=st.session_state.interests,
                                 help="E.g., history, cheap street food, photography", 
                                 key="interests_input")
        
        submitted = st.form_submit_button("Generate Budget Itinerary", type="primary")

    if submitted:
        if not all([destination, days, interests]):
            st.warning("Please fill in all the required fields.")
            return

        # Save inputs to session state
        st.session_state.destination = destination
        st.session_state.days = days
        st.session_state.interests = interests

        with st.spinner("🧠 Generating your optimized itinerary... This may take a moment."):
            status_message, itinerary_data = generate_student_itinerary(
                destination=destination,
                days=days,
                interests=interests
            )

        # Display Results
        if "successfully" in status_message:
            st.success(status_message)
            st.session_state.itinerary_data = itinerary_data
        else:
            st.session_state.itinerary_data = None
            st.error(status_message)
            
    # Display the itinerary below the form if data exists
    if st.session_state.itinerary_data:
        display_itinerary_streamlit(st.session_state.itinerary_data)
        
        # Show Maps, Charts, Weather after itinerary generation
        render_trip_tools(st.session_state.destination)

# --- Page 2: Popular Places & Travel Tips (Using local images) ---

def render_popular_places_page():
    """Renders a section with popular budget destinations and tips, including local image paths."""
    st.header("📍 Popular Budget Destinations & Tips")
    st.markdown("---")
    
    st.subheader("Top 3 Student Budget Destinations")
    
    # Data structure using local image paths
    places = [
        {"city": "Goa, India", "tip": "Rent a scooter for cheap local travel. Use local beach shacks for budget meals and accommodation.", "cost_rating": "₹₹", 
         "image_path": "./images/goa.jpeg"}, 
        {"city": "Pondicherry, India", "tip": "Explore the French Quarter by bicycle. Use local bus services for cheap inter-city travel.", "cost_rating": "₹", 
         "image_path": "./images/pondicherry.jpeg"},
        {"city": "Kathmandu, Nepal", "tip": "Nepal is very budget-friendly. Stay in Thamel and enjoy cheap trekking supplies and food.", "cost_rating": "NPR (low cost)", 
         "image_path": "./images/katmandu.jpeg"},
    ]
    
    cols = st.columns(3)
    
    for i, place in enumerate(places):
        with cols[i]:
            # Use st.image() with the local file path
            try:
                st.image(place["image_path"], caption=place["city"])
            except FileNotFoundError:
                st.warning(f"Image not found for {place['city']} at path: {place['image_path']}")
                
            st.metric(label=f"💰 {place['cost_rating']} | {place['city']}", value="Must Visit!")
            st.markdown(f"**Budget Tip:** {place['tip']}")
            st.button(f"Plan a trip to {place['city'].split(',')[0]}", key=f"plan_{i}", use_container_width=True, 
                      on_click=lambda c=place['city']: st.session_state.update(current_page="Plan Trip", destination=c))


    st.subheader("Essential Budget Travel Advice")
    st.markdown("""
    - **Hostels over Hotels:** Choose accommodation with a kitchen to save money by cooking your own meals.
    - **Free Attractions:** Prioritize free activities like public parks, temples, and self-guided walking tours.
    - **Public Transport:** Use buses (State Transport) or trains (sleeper class) over private taxis for inter-city travel to save costs.
    - **Street Food:** Embrace local *dhabas* and street vendors for meals under ₹100. Always check hygiene first!
    """)

# --- Page 3: AI Chatbot (Improved Logic) ---

def render_chat_page():
    """Renders a conversational chat interface powered by Gemini 2.5 Flash."""
    
    st.header("💬 AI Chat: Ask Anything!")
    st.markdown("---")

    if not GEMINI_CLIENT:
        st.error("🚨 Gemini Chat is unavailable. Check your API Key configuration.")
        return
        
    # Set up session state for chat history
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "model", "content": "Hello! I'm a helpful AI assistant. How can I help you plan your next budget trip or answer a general question?"}
        ]
        
    # Set a system instruction for the chat
    system_instruction = (
        "You are a friendly, helpful AI assistant. You specialize in budget travel, itinerary planning, "
        "and general knowledge. Keep responses concise, supportive, and informative."
    )
    
    # Helper function to format chat history for the Gemini API
    def get_api_contents(history):
        """Converts Streamlit session state history to the format required by the Gemini API."""
        return [
            Content(
                role=m["role"],
                parts=[Part.from_text(text=m["content"])]
            )
            for m in history
        ]

    # Display chat messages from history
    for msg in st.session_state.messages:
        avatar = "🤖" if msg["role"] == "model" else "🚶"
        with st.chat_message(msg["role"], avatar=avatar):
            st.write(msg["content"])

    # Accept user input
    if prompt := st.chat_input("Ask a question about travel, Gemini, or anything else..."):
        # Add user message to history and display it
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🚶"):
            st.write(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            
            # Get the complete conversation history for the API call
            contents = get_api_contents(st.session_state.messages)
            
            try:
                response_stream = GEMINI_CLIENT.models.generate_content_stream(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction
                    )
                )

                # Use st.write_stream to display the response chunks as they arrive
                # Only use chunks that have text content
                full_response = st.write_stream((chunk.text for chunk in response_stream if chunk.text))
                
                # Append the full response using 'model' role to the session state
                st.session_state.messages.append({"role": "model", "content": full_response})
                
            except Exception as e:
                error_message = f"An error occurred: {e}"
                st.error(error_message)
                st.session_state.messages.append({"role": "model", "content": error_message})

# --- Page 4: About Page ---

def render_about_page():
    """Renders the simplified About section."""
    st.header("📚 About the AI Student Travel Planner")
    st.markdown("---")

    st.subheader("Mission")
    st.markdown(
        """
        This application is powered by **Google's Gemini model** and is designed specifically for students and budget-conscious travelers. 
        Our mission is to create a detailed, efficient, and fun travel plan that prioritizes **free or low-cost activities (under ₹500 INR)**.
        
        * **Currency:** All estimates are provided in **Indian Rupee (₹)**.
        * **Technology:** Gemini 2.5 Flash is used for fast, accurate planning and real-time chat.
        * **Focus:** Creating highly efficient itineraries that minimize travel costs and time by grouping nearby activities.
        """
    )
    
    st.markdown("---")
    
    st.subheader("How It Works")
    st.markdown(
        """
        1. **Plan Trip:** You provide a destination and your interests. Gemini generates a structured, day-by-day itinerary in a machine-readable JSON format, focusing strictly on budget travel. After generation, interactive **Map and Weather tools** appear to help you prepare.
        2. **AI Chat:** This is a general-purpose assistant where you can ask any questions, travel-related or otherwise, powered by Gemini in a conversational style.
        3. **Popular Places:** Provides static suggestions for great budget destinations and essential, money-saving travel tips, complete with destination photos.
        """
    )


# --- Main Streamlit App Logic ---

def main():
    st.set_page_config(
        page_title="AI Student Travel Planner (INR)",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("✈️ AI Student Travel Planner")
    st.markdown("### Personalized, Budget-Friendly Itineraries (All Costs in ₹ INR)")
    # st.markdown("---") was removed here
    
    # Initialize current page if not set
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Plan Trip"
        
    # --- Sidebar Navigation ---
    with st.sidebar:
        st.header("Navigation")
        page_options = {
            "Plan Trip": "💡 Plan Trip & Itinerary",
            "Popular Places": "📍 Popular Places & Tips",
            "AI Chat": "💬 AI Chat (Gemini)",
            "About": "📚 About the Planner" 
        }
        
        selection = st.radio(
            "Go to",
            options=list(page_options.keys()),
            format_func=lambda x: page_options[x],
            key="page_selection"
        )
        st.session_state.current_page = selection
        
        st.markdown("---")
        st.info("The Plan Trip and Chat features require a working Gemini API key.")


    # --- Main Content Rendering based on Selection ---
    if st.session_state.current_page == "Plan Trip":
        render_plan_trip_page()
    
    elif st.session_state.current_page == "Popular Places":
        render_popular_places_page()
        
    elif st.session_state.current_page == "AI Chat":
        render_chat_page()
        
    elif st.session_state.current_page == "About": 
        render_about_page()

if __name__ == "__main__":
    main()
