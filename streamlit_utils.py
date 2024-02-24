import pandas as pd
import streamlit as st

def data_editor_on_change(data_editor_key, df_key):
    state = st.session_state[data_editor_key]
    for index, updates in state["edited_rows"].items():
        for key, value in updates.items():
            st.session_state[df_key].loc[st.session_state[df_key].index == index, key] = value
    for updates in state["added_rows"]:
        st.session_state[df_key] = pd.concat([st.session_state[df_key], 
                                                    pd.DataFrame(updates,index=[0])],
                                                    ignore_index=True)
    for index in state["deleted_rows"]:
        st.session_state[df_key] = st.session_state[df_key].drop(index=index)