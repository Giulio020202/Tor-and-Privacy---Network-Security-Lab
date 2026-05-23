import streamlit as st
import pandas as pd
import sys
import os

# check file in input as argument
if len(sys.argv) != 3:
    raise Exception("arguments must be four")

print(sys.argv)

if not os.path.exists(sys.argv[2]):
    raise Exception ("dataset does not exist")

page = st.sidebar.radio("Datasets", ["Patients", "Voters"])

# function to show the description of a dataset
def show_dataframe(dt):

    st.subheader("Dataset Overview")

    if st.checkbox('Shape'):
        st.write("Shape:", df.shape)

    if st.checkbox('Head (first 6 rows)'):
        st.dataframe(df.head(6), hide_index=True)
    
    if st.checkbox('Tail (last 6 rows)'):
        st.dataframe(df.tail(6), hide_index=True)

# create a page for the patients dataset
if page == "Patients":
    st.write(
        """
        # Patients
        Dataset of patients
        """
    )
    df = pd.read_csv(sys.argv[2], index_col=False)
    df = df.reset_index(drop=True)

    # store session state without shuffle
    if "view_df" not in st.session_state:
        st.session_state.view_df = df
    # create a button to shuffle the dataset
    if st.button("Shuffle dataset"):
        st.session_state.view_df = st.session_state.view_df.sample(
            frac=1
        ).reset_index(drop=True)
    st.dataframe(st.session_state.view_df, hide_index=True)
    show_dataframe(df)

    # create a rows visualizer
    st.subheader("Row Selector")
    row_id = st.selectbox(
        "Select row index",
        df.index
    )
    st.dataframe(df.iloc[[row_id]], hide_index=True)
elif page == "Voters":  # create voters' page
    st.write(
        """
        # Voters
        Dataset of voters
        """
    )
    df = pd.read_csv("voters.csv", index_col=False)
    df = df.reset_index(drop=True)
    st.dataframe(df, hide_index=True)
    show_dataframe(df)