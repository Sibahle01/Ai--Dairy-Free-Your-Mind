# app.py
import streamlit as st
from classifier import RobustJournalClassifier
from database import (
    init_db,
    save_entry,
    get_entries_df,
    auto_process_entry_for_goals,
    delete_entry,
    get_goals_df,
    update_goal
)

# ------------------- Initialize -------------------
st.set_page_config(page_title="AI Diary Assistant", layout="wide")
st.title("AI Diary Assistant")
init_db()

classifier = RobustJournalClassifier()

# ------------------- Tabs -------------------
tabs = st.tabs(["Add Entry", "Browse Entries", "Goals Dashboard"])

# ------------------- Tab 1: Add Entry -------------------
with tabs[0]:
    st.header("Add a New Diary Entry")

    entry_text = st.text_area("Write your entry here:", key="entry_textarea")

    if st.button("Classify Entry", key="classify_entry"):
        if entry_text.strip():
            result = classifier.classify_single(entry_text)
            st.write("### Classification Result")
            st.json({
                "entry": result.entry,
                "main_category": result.main_category,
                "secondary_category": result.secondary_category,
                "sub_category": result.sub_category,
                "confidence_scores": result.confidence_scores,
                "sub_confidence": result.sub_confidence,
                "processing_time": result.processing_time,
                "success": result.success,
                "error_message": result.error_message
            })
        else:
            st.warning("Please enter some text first!")

    if st.button("Submit Entry", key="submit_entry"):
        if entry_text.strip():
            result = classifier.classify_single(entry_text)
            entry_id = save_entry(result)
            auto_process_entry_for_goals(
                entry_id, result.entry, result.main_category, result.sub_category
            )
            st.success("Entry saved successfully!")
        else:
            st.warning("Cannot submit empty entry!")

# ------------------- Tab 2: Browse Entries -------------------
with tabs[1]:
    st.header("Browse Diary Entries")
    df = get_entries_df()
    if not df.empty:
        for _, row in df.iterrows():
            st.subheader(f"{row['main_category']} - {row['secondary_category'] or ''}")
            st.write(row['entry_text'])
            col1, col2 = st.columns(2)

            with col1:
                if st.button(f"Delete Entry {row['entry_id']}", key=f"del_entry_{row['entry_id']}"):
                    delete_entry(row['entry_id'])
                    st.success("Entry deleted!")
                    st.experimental_rerun()

            with col2:
                st.write(f"Tags: {', '.join(row['tags'])}")
    else:
        st.info("No diary entries yet.")

# ------------------- Tab 3: Goals Dashboard -------------------
with tabs[2]:
    st.header("Goals Dashboard")
    df_goals = get_goals_df()
    if not df_goals.empty:
        for _, row in df_goals.iterrows():
            st.write(
                f"{row['goal_text']} — Status: {row['status']} — Updated: {row['updated_at']}"
            )

            goal_text = st.text_input(
                f"Edit Goal {row['goal_id']}",
                value=row['goal_text'],
                key=f"goal_text_{row['goal_id']}",
            )

            status_options = ["planned", "in_progress", "completed", "dropped"]
            status_index = (
                status_options.index(row['status']) if row['status'] in status_options else 0
            )
            status = st.selectbox(
                f"Status", status_options, index=status_index, key=f"status_{row['goal_id']}"
            )

            if st.button(f"Update Goal {row['goal_id']}", key=f"update_goal_{row['goal_id']}"):
                update_goal(row['goal_id'], goal_text, status)
                st.success("Goal updated!")
                st.experimental_rerun()
    else:
        st.info("No goals tracked yet.")
