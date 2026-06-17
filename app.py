import os
import streamlit as st
import pandas as pd
from data.session_state import (
    init_session_state, save_preferences_to_browser, save_to_last_meals, 
    get_current_phase, advance_phase, reset_cooking_session
)
from agents.ingredient_parser import parse_ingredients
from agents.recipe_finder import find_recipes
from agents.recipe_personalizer import personalize_recipes
from agents.recipe_teacher import generate_masterclass
from agents.recipe_presenter import present_recipe
from agents.panic_mode import get_panic_fix, get_common_problems
from utils.pdf_generator import generate_recipe_pdf


st.set_page_config(page_title="Bawarchi Ease", layout="wide")

init_session_state()

if "step" not in st.session_state:
    st.session_state["step"] = "input"

step = st.session_state["step"]

# --- STEP 1: input ---
if step == "input":
    st.markdown("""

    <style>
    @keyframes float {
      0% { transform: translateY(0px) rotate(0deg); }
      50% { transform: translateY(-6px) rotate(3deg); }
      100% { transform: translateY(0px) rotate(0deg); }
    }
    @keyframes steamRise {
      0% { opacity: 1; transform: translateY(0px); }
      50% { opacity: 0.3; transform: translateY(-4px); }
      100% { opacity: 1; transform: translateY(0px); }
    }
    .mascot-container {
      display: inline-block;
      animation: float 3s ease-in-out infinite;
      margin-left: 10px;
      vertical-align: middle;
    }
    .steam-path {
      animation: steamRise 2s ease infinite;
    }
    </style>
    """, unsafe_allow_html=True)

    header_html = """
    <h1 style="display: flex; align-items: center; gap: 10px; margin: 0; font-size: 2.2rem;">
      Bawarchi Ease – Your AI Kitchen Mentor
      <div class="mascot-container">
        <svg width="45" height="45" viewBox="0 0 24 24" fill="none" stroke="#E67E22" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path class="steam-path" d="M9 3c0 1-1 1-1 2s1 1 1 2" style="animation-delay: 0s;"/>
          <path class="steam-path" d="M12 2c0 1-1 1-1 2s1 1 1 2" style="animation-delay: 0.4s;"/>
          <path class="steam-path" d="M15 3c0 1-1 1-1 2s1 1 1 2" style="animation-delay: 0.8s;"/>
          <path d="M4 10h16v8a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-8z" />
          <path d="M2 10h20" />
          <path d="M10 10V8h4v2" />
        </svg>
      </div>
    </h1>
    <h3 style="margin-top: 5px; color: #555; font-weight: normal;">آپ کے باورچی خانے کا ذہین ساتھی</h3>
    """
    st.markdown(header_html, unsafe_allow_html=True)

    col1, col2 = st.columns([6, 4])
    
    with col2:
        with st.expander("My Preferences", expanded=True):
            prefs = st.session_state["preferences"]
            
            family_size = st.slider("Family Size", 1, 8, prefs.get("family_size", 4))
            
            spice_idx = ["mild", "medium", "spicy"].index(prefs.get("spice_level", "medium"))
            spice_level = st.selectbox("Spice Level", ["mild", "medium", "spicy"], index=spice_idx)
            
            max_time_minutes = st.slider("Max Cooking Time (min)", 15, 90, prefs.get("max_time_minutes", 45))
            dietary_restrictions = st.multiselect("Dietary Restrictions", ["Vegetarian", "Halal", "Gluten-free"], default=prefs.get("dietary_restrictions", []))
            
            # Output language
            lang_mapping = {"English": "english", "English + Urdu": "both", "Urdu Only": "urdu"}
            rev_mapping = {v: k for k, v in lang_mapping.items()}
            current_lang = prefs.get("output_language", "english")
            output_language_label = st.radio("Recipe instructions in:", ["English", "English + Urdu", "Urdu Only"], index=["English", "English + Urdu", "Urdu Only"].index(rev_mapping.get(current_lang, "English")))
            
            if st.button("Save Preferences"):
                st.session_state["preferences"].update({
                    "family_size": family_size,
                    "spice_level": spice_level,
                    "max_time_minutes": max_time_minutes,
                    "dietary_restrictions": dietary_restrictions,
                    "output_language": lang_mapping[output_language_label]
                })
                save_preferences_to_browser(st.session_state["preferences"])
                st.success("Preferences saved!")
                
    with col1:
        ingredients_input = st.text_area("Ingredients", placeholder="e.g. chicken, tomatoes, rice / چکن، ٹماٹر، چاول")
        uploaded_image = st.file_uploader("Or upload a pantry photo", type=["jpg", "jpeg", "png"])
        
        if st.button("Find Recipes", type="primary"):
            try:
                with st.spinner("Scanning your ingredients..."):
                    image_bytes = uploaded_image.getvalue() if uploaded_image else None
                    parsed = parse_ingredients(ingredients_input, image_bytes)
                    
                extracted_ingredients = parsed.get("ingredients", [])
                st.session_state["ingredients"] = extracted_ingredients
                
                if extracted_ingredients:
                    with st.spinner("Searching Pakistani recipes..."):
                        raw_recipes = find_recipes(extracted_ingredients, st.session_state["preferences"])
                        
                    with st.spinner("Personalizing for your family..."):
                        top_recipes = personalize_recipes(raw_recipes, st.session_state["preferences"])
                        
                    st.session_state["recipes"] = top_recipes
                    st.session_state["step"] = "select"
                    st.rerun()
                else:
                    st.error("Could not detect any ingredients. Please try again.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# --- STEP 2: select ---
elif step == "select":
    st.header("Recipes Found for You 👨‍🍳")
    recipes = st.session_state.get("recipes", [])
    
    if not recipes:
        st.warning("No recipes found. Let's try again.")
        if st.button("Go Back"):
            st.session_state["step"] = "input"
            st.rerun()
            
    for recipe in recipes:
        with st.expander(f"{recipe.get('title')} - {recipe.get('why_recommended')}", expanded=True):
            st.write(f"**Ready in:** {recipe.get('readyInMinutes')} mins | **Servings:** {recipe.get('servings')} | **Score:** {recipe.get('personalization_score')}")
            
            if st.button(f"Cook This! ({recipe.get('title')})", key=f"cook_{recipe.get('id', recipe.get('title'))}"):
                try:
                    with st.spinner("Preparing your masterclass..."):
                        masterclass = generate_masterclass(recipe)
                        
                    with st.spinner("Generating recipe card..."):
                        presented = present_recipe(masterclass, st.session_state["preferences"])
                        
                    st.session_state["selected_recipe"] = recipe
                    st.session_state["masterclass"] = masterclass
                    st.session_state["presented_card"] = presented
                    st.session_state["current_phase_index"] = 0
                    st.session_state["step"] = "cook"
                    st.rerun()
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
                    
    if st.button("Back to Input"):
        st.session_state["step"] = "input"
        st.rerun()

# --- STEP 3: cook ---
elif step == "cook":
    card = st.session_state.get("presented_card", {})
    masterclass = st.session_state.get("masterclass", {})
    
    col1, col2 = st.columns(2)
    with col1:
        st.header(card.get("recipe_title", ""))
    with col2:
        if card.get("show_urdu"):
            st.header(card.get("title_urdu", ""))
            
    phases = card.get("phases", [])
    total_phases = len(phases)
    current_idx = st.session_state["current_phase_index"]
    
    if total_phases > 0:
        progress = (current_idx + 1) / total_phases
        st.progress(progress, text=f"Phase {current_idx + 1} of {total_phases}")
        
    phase = get_current_phase()
    if phase:
        with st.container(border=True):
            st.subheader(f"Phase {phase.get('phase_number', current_idx+1)}: {phase.get('phase_name', '')}")
            st.caption(f"Technique: {phase.get('technique', '')}")
            
            st.write("**What to do:**")
            if not card.get("instructions_english_hidden"):
                st.write(phase.get("what_to_do", ""))
            
            if card.get("show_urdu") and "instructions_urdu" in phase:
                st.write(phase.get("instructions_urdu", ""))
                
            st.info(f"**The Lesson:** {phase.get('the_lesson', '')}")
            st.success(f"**Sensory Cue:** {phase.get('sensory_cue', '')}")
            
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("✅ Phase Done →", use_container_width=True):
                if current_idx < total_phases - 1:
                    advance_phase()
                else:
                    st.session_state["step"] = "done"
                st.rerun()
                
        with col_btn2:
            with st.popover("🆘 Something Went Wrong", use_container_width=True):
                with st.form("panic_form"):
                    common_probs = get_common_problems(phase.get("phase_name", ""))
                    selected_prob = st.radio("Common issues:", common_probs)
                    custom_prob = st.text_input("Or describe the problem:")
                    
                    if st.form_submit_button("Get Help"):
                        try:
                            with st.spinner("Getting your fix..."):
                                prob_desc = custom_prob if custom_prob else selected_prob
                                fix = get_panic_fix(phase, prob_desc)
                                st.error(f"**What went wrong:** {fix.get('what_went_wrong', '')}")
                                st.warning(f"**Immediate Fix:** {fix.get('immediate_fix', '')}")
                                st.info(f"**Prevention:** {fix.get('prevention', '')}")
                        except Exception as e:
                            st.error(f"Something went wrong: {e}")
                            
    with st.sidebar:
        st.subheader("Recipe Info")
        st.write(f"**Cooking Time:** {card.get('cooking_time', '')}")
        st.write(f"**Difficulty:** {card.get('difficulty', '')}")

        
        st.subheader("Grocery List")
        unit_system_label = st.radio("Measurement System:", ["Metric", "US Standard", "Desi (Tola/Pau/Ser)"], index=0)
        unit_system = {"Metric": "metric", "US Standard": "us", "Desi (Tola/Pau/Ser)": "desi"}[unit_system_label]
        
        ingredients_detailed = card.get("ingredients_detailed", [])
        if ingredients_detailed:
            for ing in ingredients_detailed:
                name = ing.get("name", "")
                if unit_system == "us":
                    measure = ing.get("us", "")
                elif unit_system == "desi":
                    measure = ing.get("desi", "")
                else:
                    measure = ing.get("metric", "")
                st.write(f"- **{name}**: {measure}")
        else:
            grocery_list = card.get("grocery_list", [])
            for item in grocery_list:
                st.write(f"- {item}")
            
        if card:
            pdf_bytes = generate_recipe_pdf(card, unit_system)
            recipe_title_slug = card.get("recipe_title", "recipe").lower().replace(" ", "_")
            st.download_button(
                label="📄 Download Recipe PDF",
                data=pdf_bytes,
                file_name=f"{recipe_title_slug}_recipe.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            
        if st.button("Quit Cooking"):
            reset_cooking_session()
            st.session_state["step"] = "input"
            st.rerun()

# --- STEP 4: done ---
elif step == "done":
    st.balloons()
    st.header("Cooking Complete! 🎉")
    
    card = st.session_state.get("presented_card", {})
    if card:
        save_to_last_meals(card.get("recipe_title", "Unknown"))
        
        with st.expander("Full Recipe Card", expanded=True):
            st.subheader(card.get("recipe_title", ""))
            for phase in card.get("phases", []):
                st.write(f"**{phase.get('phase_name', '')}**: {phase.get('what_to_do', '')}")
                
    if st.button("Cook Another Dish", type="primary"):
        reset_cooking_session()
        st.session_state["step"] = "input"
        st.rerun()

# --- Debug Panel ---
debug_mode = str(os.getenv("DEBUG", "")).lower() == "true"
try:
    if "DEBUG" in st.secrets and str(st.secrets["DEBUG"]).lower() == "true":
        debug_mode = True
except Exception:
    pass

if debug_mode:
    with st.sidebar.expander("Debug Panel", expanded=False):
        st.json(st.session_state)
