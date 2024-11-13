import streamlit as st

def UI():
    st.markdown("""  
    <!-- Link ke Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">

    <div style="width: 100%; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #343a40; box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.2); border-radius: 8px; font-family: 'Poppins', sans-serif;">
        <div style="padding: 20px; background-color: #212529; border-radius: 8px;">
            <h3 style="color: #f8f9fa; margin: 0; font-weight: 600; text-align: center;">GSP Partnership Value Dashboard</h3>
        </div>
    </div>

    <style>
        /* Mengubah font pada elemen expander */
        div[data-testid="stExpander"] div[role="button"] p {
            font-size: 1.1rem;
            font-family: 'Poppins', sans-serif;
        }

        /* Mengubah font pada semua teks */
        * {
            font-family: 'Poppins', sans-serif;
        }
    </style>
    """, unsafe_allow_html=True)

# Memanggil fungsi UI untuk menampilkan di Streamlit
