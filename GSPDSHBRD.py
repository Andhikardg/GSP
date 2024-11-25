import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import datetime
from ui import *
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import openpyxl
from gspread_dataframe import set_with_dataframe

UI()
st.markdown('##')
def connect_to_gsheet(creds_json, spreadsheet_name):
    scope = ["https://spreadsheets.google.com/feeds", 
             "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file",
             "https://www.googleapis.com/auth/drive"]

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(credentials)
    spreadsheet = client.open(spreadsheet_name)
    return spreadsheet

SPREADSHEET_NAME = 'GSP'
SHEET_NAME = 'Sheet1'
credentials = {
  "type": st.secrets.type, 
  "project_id": st.secrets.project_id,
  "private_key_id": st.secrets.private_key_id,
  "private_key": st.secrets.private_key,
    "client_email": st.secrets.client_email,
  "client_id": st.secrets.client_id,
  "auth_uri": st.secrets.auth_uri,
  "token_uri": st.secrets.token_uri,
  "auth_provider_x509_cert_url": st.secrets.auth_provider_x509_cert_url,
  "client_x509_cert_url": st.secrets.client_x509_cert_url,
  "universe_domain": st.secrets.universe_domain
}


spreadsheet = connect_to_gsheet(credentials, SPREADSHEET_NAME)


def read_data(spreadsheet, SHEET_NAME):
    worksheet = spreadsheet.worksheet(SHEET_NAME)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

df = read_data(spreadsheet, 'Sheet1')
df['Month'] = df['Month'].str.strip().str.title()

if 'df' not in st.session_state:
    st.session_state.df = df  

def Analytics(df):
    df_realisasinotnol = df[df['Realisasi']!=0]
    cumsum = df_realisasinotnol['Realisasi'].cumsum()
    cumsum = pd.Series(cumsum).reindex(df.index, fill_value=0)
    df['Monthly_Ach'] = (df['Realisasi'] / df['Target']) * 100  # Monthly achievement in percentage
    df['Cumul_Realisasi'] = cumsum # Cumulative realization
    df['Cumul_Target'] = df['Target'].cumsum()  # Cumulative target

    # Define the quarters
    quarters = {
        "Q1": ["January", "February", "March"],
        "Q2": ["April", "May", "June"],
        "Q3": ["July", "August", "September"],
        "Q4": ["October", "November", "December"]
    }

    # Initialize the columns for quarterly achievement and cumulative quarterly achievement
    df['Quarterly_Ach'] = None
    df['Cumul_quarterly'] = None

    cumulative_realisasi = 0
    cumulative_target = 0

    # Loop over each quarter and calculate quarterly and cumulative quarterly achievements
    for quarters, months in quarters.items():
        # Calculate the total Realisasi and Target for each quarter
        total_realisasi = df[df['Month'].isin(months)]['Realisasi'].sum()
        total_target = df[df['Month'].isin(months)]['Target'].sum()

        # Update cumulative realizations and targets
        cumulative_realisasi += total_realisasi
        cumulative_target += total_target

        # Calculate the quarterly achievement (Realisasi / Target) * 100
        quarterly_ach = (total_realisasi / total_target) * 100 if total_target > 0 else 0

        # Assign the quarterly achievement to the corresponding months
        df.loc[df['Month'].isin(months), 'Quarterly_Ach'] = quarterly_ach

        # Calculate the cumulative quarterly achievement (Cumul_quarterly = cumulative Realisasi / cumulative Target) * 100
        if cumulative_target > 0:
            cumul_quarterly_ach = (cumulative_realisasi / cumulative_target) * 100
        else:
            cumul_quarterly_ach = 0  # To avoid division by zero

        # Assign the cumulative quarterly achievement to the corresponding months
        df.loc[df['Month'].isin(months), 'Cumul_quarterly'] = cumul_quarterly_ach

    # Total sum of all targets for the year
    total_target = df['Target'].sum()

    # Calculate Cumul_vs_Yearly as cumulative sum of Realisasi divided by total target sum
    df['Cumul_vs_Yearly'] = (df['Cumul_Realisasi'] / total_target) * 100
    

    return df

def show(df):
# Ensure the cumulative yearly achievement values for the latest and previous month
    latest_cumulative_yearly = df['Cumul_vs_Yearly'].iloc[-1] if pd.notna(df['Cumul_vs_Yearly'].iloc[-1]) else 0
    previous_cumulative_yearly = df['Cumul_vs_Yearly'].iloc[-2] if pd.notna(df['Cumul_vs_Yearly'].iloc[-2]) else 0

    # Calculate the percentage change in cumulative yearly achievement
    if previous_cumulative_yearly != 0:
        cumulative_yearly_change = ((latest_cumulative_yearly - previous_cumulative_yearly) / previous_cumulative_yearly) * 100
    else:
        cumulative_yearly_change = 0  # To avoid division by zero if there's no previous data

    # Compact metrics boxes for Monthly Profit Change, Target Change, and Cumulative Yearly Achievement Change
    col2, col3 = st.columns(2)

    with col2:
        Total_realisasi_year = df['Realisasi'].sum()
        total_target_year = df['Target'].sum()
        if total_target_year != 0:
            month_to_date_achievement = (Total_realisasi_year / total_target_year) * 100
        else:
            month_to_date_achievement = 0
        st.metric(label="Month to Date Achievement", value=f"{month_to_date_achievement:.2f}%")

    with col3:
        df_notnull = df[df['Cumul_Realisasi']!=0].reset_index(drop=True)
        Cumulative_realisasi = df_notnull['Cumul_Realisasi']
        if len(Cumulative_realisasi) > 1 :
            latest_cumulative = Cumulative_realisasi.iloc[-1] 
            previous_cumulative = Cumulative_realisasi.iloc[-2] 
            if previous_cumulative != 0:
                mom_growth = ((latest_cumulative - previous_cumulative) / previous_cumulative) * 100
            else:
                mom_growth = 0
        else:
            mom_growth = 0
        st.metric(
            label="Month Over Month Growth", 
            value=f"{mom_growth:.2f}%", 
        )

def show2(df):
    # Create a Plotly figure for Monthly Achievement, Target, and Realisasi
    fig = go.Figure()
    # Add bars for Realisasi (with ocean-themed colors)
    fig.add_trace(go.Bar(
        x=df['Month'],
        y=df['Realisasi'],
        name='Realisasi',
        marker_color='#20B2AA',  # Light Sea Green (ocean theme)
        hoverinfo='text',
        hovertext=[f'Month: {month}<br>Realisasi: {realisasi:.2f} Miliar' for month, realisasi in zip(df['Month'], df['Realisasi'])]
    ))
    
    # Add bars for Target (using an ocean-themed color)
    fig.add_trace(go.Bar(
        x=df['Month'],
        y=df['Target'],
        name='Target',
        marker_color='#1E90FF',  # Ocean blue
        hoverinfo='text',
        hovertext=[f'Month: {month}<br>Target: {target:.2f} Miliar' for month, target in zip(df['Month'], df['Target'])]
    ))

    # Calculate the position of the text above both bars (Target and Realisasi)
    text_position = [max(target, realisasi) + 1 for target, realisasi in zip(df['Target'], df['Realisasi'])]

    # Add text (Monthly Achievement) above both bars
    fig.add_trace(go.Scatter(
        x=df['Month'],
        y=text_position,  # Position the text slightly above the higher of the two bars
        mode='text',
        text=[f'{ach:.2f}%' for ach in df['Monthly_Ach']],
        textposition='top center',
        showlegend=False  # Disable legend for this text trace
    ))

    # Customize the layout
    fig.update_layout(
        title={
            'text': 'Monthly Performance non Cumulative',
            'font': {'size': 24},  # Title font size
            'x': 0.5,  # Center title
            'xanchor': 'center'
        },
        xaxis_tickangle=-45,
        barmode='group',
        xaxis_title='Month',
        yaxis_title='IDR Billion',
        legend_title='Metrics',
        yaxis=dict(
            range=[0, 50],
            tickformat=',.0f'
        )
    )

    # Update hover text for achievement percentages
    fig.data[2].hoverinfo = 'text'
    fig.data[2].hovertext = [f'Month: {month}<br>Achievement: {ach:.2f}%' for month, ach in zip(df['Month'], df['Monthly_Ach'])]

    # Display the updated plot
    st.plotly_chart(fig)

def show3(df):
    # Visualization for Quarterly Achievement
    # st.markdown("Whole Acumulated Performance Year Achievement (Quarterly)")
    # Calculate cumulative sums for Target and Realisasi
    df['Cumulative_Target'] = df['Target'].cumsum()  # Cumulative sum for Target
    df['Cumulative_Realisasi'] = df['Realisasi'].cumsum()  # Cumulative sum for Realisasi

# Cumulative monthly

    # Update figure
    fig = go.Figure()
    
    # Add bars for Cumulative Realisasi
    fig.add_trace(go.Bar(
        x=df['Month'],
        y=df['Cumulative_Realisasi'],
        name='Cumulative Realisasi',
        marker_color='#20B2AA',  # Light Sea Green (ocean theme)
        hoverinfo='text',
        hovertext=[f'Month: {month}<br>Cumulative Realisasi: {realisasi:.2f} Miliar' for month, realisasi in zip(df['Month'], df['Cumulative_Realisasi'])]
    ))

    # Add bars for Cumulative Target
    fig.add_trace(go.Bar(
        x=df['Month'],
        y=df['Cumulative_Target'],
        name='Cumulative Target',
        marker_color='#1E90FF',  # Ocean blue
        hoverinfo='text',
        hovertext=[f'Month: {month}<br>Cumulative Target: {target:.2f} Miliar' for month, target in zip(df['Month'], df['Cumulative_Target'])]
    ))

    # Calculate the position of the text above both bars (Cumulative Target and Realisasi)
    text_position = [max(target, realisasi) + 1 for target, realisasi in zip(df['Cumulative_Target'], df['Cumulative_Realisasi'])]

    # Add text (Cumulative Achievement) above both bars
    fig.add_trace(go.Scatter(
        x=df['Month'],
        y=text_position,  # Position the text slightly above the higher of the two bars
        mode='text',
        text=[f'{ach:.2f}%' for ach in df['Monthly_Ach']],  # Assuming Monthly_Ach is already cumulative
        textposition='top center',
        showlegend=False  # Disable legend for this text trace
    ))

    # Customize the layout
    fig.update_layout(
        title={
            'text': 'Monthly Performance Cumulative',
            'font': {'size': 24},  # Title font size
            'x': 0.5,  # Center title
            'xanchor': 'center'
        },
        xaxis_tickangle=-45,
        barmode='group',
        xaxis_title='Month',
        yaxis_title='IDR Billion',
        legend_title='Metrics',
        yaxis=dict(
            range=[0, df['Cumulative_Target'].max() + 10],  # Adjust the range based on cumulative data
            tickformat=',.0f'
        )
    )

    # Update hover text for cumulative achievement percentages
    fig.data[2].hoverinfo = 'text'
    fig.data[2].hovertext = [f'Month: {month}<br>Cumulative Achievement: {ach:.2f}%' for month, ach in zip(df['Month'], df['Monthly_Ach'])]

    # Display the updated plot
    st.plotly_chart(fig)

def show4(df):
    # non cumulative Quarterly 
    # Define quarters to group months
    quarter_mapping = {
        "January": "Q1", "February": "Q1", "March": "Q1",
        "April": "Q2", "May": "Q2", "June": "Q2",
        "July": "Q3", "August": "Q3", "September": "Q3",
        "October": "Q4", "November": "Q4", "December": "Q4"
    }

    # Map the months to their respective quarters
    df['Quarter'] = df['Month'].map(quarter_mapping)

    # Create a new DataFrame for quarterly achievement, realisasi, and target
    quarterly_data = df.groupby('Quarter', as_index=False).agg({
        'Monthly_Ach': 'mean',  # Average achievement per quarter
        'Target': 'mean',       # Average target per quarter
        'Realisasi': 'sum'      # Sum of Realisasi per quarter
    })

    # Create the bar plot for Quarterly Achievement, Realisasi, and Target
    fig_quarterly_bar = go.Figure()

    # Add bars for Realisasi per quarter
    fig_quarterly_bar.add_trace(go.Bar(
        x=quarterly_data['Quarter'],
        y=quarterly_data['Realisasi'],
        name='Realisasi',
        marker_color='green',
        hoverinfo='text',
        hovertext=[f'Quarter: {quarter}<br>Realisasi: {realisasi:.2f} Miliar' for quarter, realisasi in zip(quarterly_data['Quarter'], quarterly_data['Realisasi'])]
    ))

    # Add bars for Target per quarter
    fig_quarterly_bar.add_trace(go.Bar(
        x=quarterly_data['Quarter'],
        y=quarterly_data['Target'],
        name='Target',
        marker_color='orange',
        hoverinfo='text',
        hovertext=[f'Quarter: {quarter}<br>Target: {target:.2f} Miliar' for quarter, target in zip(quarterly_data['Quarter'], quarterly_data['Target'])]
    ))

    # Calculate the position of the text (Quarterly Achievement) above both bars (Target and Realisasi)
    text_position = [max(target, realisasi) + 1 for target, realisasi in zip(quarterly_data['Target'], quarterly_data['Realisasi'])]

    # Add text (Quarterly Achievement) above both bars
    fig_quarterly_bar.add_trace(go.Scatter(
        x=quarterly_data['Quarter'],
        y=text_position,  # Position the text slightly above the higher of the two bars
        mode='text',
        text=[f'{ach:.2f}%' for ach in quarterly_data['Monthly_Ach']],
        textposition='top center',
        showlegend=False  # Disable legend for this text trace
    ))

    # Customize the layout
    fig_quarterly_bar.update_layout(
        title={
            'text': 'Quarterly Performance non Cumulative',
            'font': {'size': 24},  # Title font size
            'x': 0.5,  # Center title
            'xanchor': 'center'
        },
        xaxis_title='Quarter',
        yaxis_title='IDR Billion',
        legend_title='Metrics',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        bargap=0.2,  # Adjust the gap between bars
        barmode='group',  # Group bars together for each quarter
        yaxis=dict(
            range=[0, max(quarterly_data['Target'].max(), quarterly_data['Realisasi'].max()) + 70],
            tickformat=',.0f',
            # Format tick labels
        )
    )

    # Update hover text for achievement percentages
    fig_quarterly_bar.data[2].hoverinfo = 'text'
    fig_quarterly_bar.data[2].hovertext = [f'Quarter: {quarter}<br>Achievement: {ach:.2f}%' for quarter, ach in zip(quarterly_data['Quarter'], quarterly_data['Monthly_Ach'])]

    # Display the bar plot
    st.plotly_chart(fig_quarterly_bar)

def show5(df):
# Cumulative Quarterly
    # Calculate cumulative sums for Target and Realisasi
    # non cumulative Quarterly 
    # Define quarters to group months
    quarter_mapping = {
        "January": "Q1", "February": "Q1", "March": "Q1",
        "April": "Q2", "May": "Q2", "June": "Q2",
        "July": "Q3", "August": "Q3", "September": "Q3",
        "October": "Q4", "November": "Q4", "December": "Q4"
    }

    # Map the months to their respective quarters
    df['Quarter'] = df['Month'].map(quarter_mapping)

    # Create a new DataFrame for quarterly achievement, realisasi, and target
    quarterly_data = df.groupby('Quarter', as_index=False).agg({
        'Monthly_Ach': 'mean',  # Average achievement per quarter
        'Target': 'mean',       # Average target per quarter
        'Realisasi': 'sum'      # Sum of Realisasi per quarter
    })
    
    quarterly_data['Cumulative_Target'] = quarterly_data['Target'].cumsum()  # Cumulative sum for Target
    quarterly_data['Cumulative_Realisasi'] = quarterly_data['Realisasi'].cumsum()  # Cumulative sum for Realisasi

    # Update figure
    fig_quarterly_bar = go.Figure()

    # Add bars for Cumulative Realisasi per quarter
    fig_quarterly_bar.add_trace(go.Bar(
        x=quarterly_data['Quarter'],
        y=quarterly_data['Cumulative_Realisasi'],
        name='Cumulative Realisasi',
        marker_color='green',
        hoverinfo='text',
        hovertext=[f'Quarter: {quarter}<br>Cumulative Realisasi: {realisasi:.2f} Miliar' for quarter, realisasi in zip(quarterly_data['Quarter'], quarterly_data['Cumulative_Realisasi'])]
    ))
    
    # Add bars for Cumulative Target per quarter
    fig_quarterly_bar.add_trace(go.Bar(
        x=quarterly_data['Quarter'],
        y=quarterly_data['Cumulative_Target'],
        name='Cumulative Target',
        marker_color='orange',
        hoverinfo='text',
        hovertext=[f'Quarter: {quarter}<br>Cumulative Target: {target:.2f} Miliar' for quarter, target in zip(quarterly_data['Quarter'], quarterly_data['Cumulative_Target'])]
    ))

    # Calculate the position of the text (Quarterly Achievement) above both bars (Cumulative Target and Realisasi)
    text_position = [max(target, realisasi) + 1 for target, realisasi in zip(quarterly_data['Cumulative_Target'], quarterly_data['Cumulative_Realisasi'])]

    # Add text (Cumulative Achievement) above both bars
    fig_quarterly_bar.add_trace(go.Scatter(
        x=quarterly_data['Quarter'],
        y=text_position,  # Position the text slightly above the higher of the two bars
        mode='text',
        text=[f'{ach:.2f}%' for ach in quarterly_data['Monthly_Ach']],  # Assuming Monthly_Ach is already cumulative
        textposition='top center',
        showlegend=False  # Disable legend for this text trace
    ))

    # Customize the layout
    fig_quarterly_bar.update_layout(
        title={
            'text': 'Quarterly Performance Cumulative',
            'font': {'size': 24},  # Title font size
            'x': 0.5,  # Center title
            'xanchor': 'center'
        },
        xaxis_title='Quarter',
        yaxis_title='IDR Billion',
        legend_title='Metrics',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        bargap=0.2,  # Adjust the gap between bars
        barmode='group',  # Group bars together for each quarter
        yaxis=dict(
            range=[0, quarterly_data['Cumulative_Target'].max() + 110],  # Adjust the range based on cumulative data
            tickformat=',.0f'
        )
    )

    # Update hover text for cumulative achievement percentages
    fig_quarterly_bar.data[2].hoverinfo = 'text'
    fig_quarterly_bar.data[2].hovertext = [f'Quarter: {quarter}<br>Cumulative Achievement: {ach:.2f}%' for quarter, ach in zip(quarterly_data['Quarter'], quarterly_data['Monthly_Ach'])]

    # Display the bar plot
    st.plotly_chart(fig_quarterly_bar)
    
def show6(df):
    # Add Cumulative Yearly Achievement Line Chart
    # st.markdown("### Cumulative Yearly Achievement per Quarter")

    # Define quarters to group months
    quarter_mapping = {
        "January": "Q1", "February": "Q1", "March": "Q1",
        "April": "Q2", "May": "Q2", "June": "Q2",
        "July": "Q3", "August": "Q3", "September": "Q3",
        "October": "Q4", "November": "Q4", "December": "Q4"
    }

    # Map the months to their respective quarters
    df['Quarter'] = df['Month'].map(quarter_mapping)

    # Group by quarter and calculate the maximum cumulative yearly achievement at the end of each quarter
    quarterly_cumulative = df.groupby('Quarter', as_index=False)['Cumul_vs_Yearly'].max()

    # Create the figure for Cumulative Yearly Achievement (line plot only)
    fig_cumulative_yearly_combined = go.Figure()

    # Add line chart for cumulative yearly achievement per quarter
    fig_cumulative_yearly_combined.add_trace(go.Scatter(
        x=quarterly_cumulative['Quarter'],
        y=quarterly_cumulative['Cumul_vs_Yearly'],
        mode='lines+markers',
        name='Cumulative Yearly Achievement (Line)',
        line=dict(color='green', width=2),
        marker=dict(size=8, symbol='circle'),
        hoverinfo='text',
        hovertext=[f'Quarter: {quarter}<br>Cumulative Achievement: {ach:.2f}%' for quarter, ach in zip(quarterly_cumulative['Quarter'], quarterly_cumulative['Cumul_vs_Yearly'])]
    ))

    # Customize the layout for the line chart
    fig_cumulative_yearly_combined.update_layout(
        title={
            'text': 'Quarterly Realization (Cumulative)/ Full Year Target (%)',
            'font': {'size': 24},  # Title font size
            'x': 0.5,  # Center title
            'xanchor': 'center'
        },
        xaxis_title='Quarter',
        yaxis_title='Cumulative Achievement (%)',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend_title='Metrics',
        yaxis=dict(
            range=[0, 100],  # Set y-axis range to 100
            tickformat=',.0f',  # Ensure the y-axis displays whole numbers
        )
    )

    # Display the cumulative yearly achievement chart (line only)
    st.plotly_chart(fig_cumulative_yearly_combined)

    # st.markdown("### Cumulative Yearly Achievement")

    # Create the line chart for Cumulative Yearly Achievement
    fig_cumulative_yearly = go.Figure()

    # Add the line chart
    fig_cumulative_yearly.add_trace(go.Scatter(
        x=df['Month'],
        y=df['Cumul_vs_Yearly'],
        mode='lines+markers',
        name='Cumulative Yearly Achievement (%)',
        line=dict(color='blue', width=2),
        marker=dict(size=8, symbol='circle'),
        hoverinfo='text',
        hovertext=[f'Month: {month}<br>Cumulative Achievement: {ach:.2f}%' for month, ach in zip(df['Month'], df['Cumul_vs_Yearly'])]
    ))

    # Customize the layout for cumulative yearly achievement chart
    fig_cumulative_yearly.update_layout(
        title={
            'text': 'Monthly Realization (Cumulative)/ Full Year Target (%)',
            'font': {'size': 24},  # Title font size
            'x': 0.5,  # Center title
            'xanchor': 'center'
        },
        xaxis_tickangle=-45,
        xaxis_title='Month',
        yaxis_title='Cumulative Achievement (%)',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend_title='Metrics',
            yaxis=dict(
            range=[0, 100],  # Set y-axis range to 100
            tickformat=',.0f',  # Ensure the y-axis displays whole numbers
        )
    )
    st.plotly_chart(fig_cumulative_yearly)

def update_gsheet(spreadsheet, sheet_name, df):
    worksheet = spreadsheet.worksheet(sheet_name)
    worksheet.clear()  
    set_with_dataframe(worksheet, df)
    
def submit_update(df, menu, spreadsheet, sheet_name):
    # Update the DataFrame
    df = st.session_state.df
    df.loc[df['Month'] == Month, 'Realisasi'] = float(Realisasi)
    df.loc[df['Month'] == Month, 'Target'] = float(Target)
    
    # Update the session state
    st.session_state.df = df
    try:
        df_update = df[['Month', 'Realisasi', 'Target']]
        update_gsheet(spreadsheet, sheet_name, df_update)
        # df.to_excel('updatedGSP.xlsx', index=False)
        st.success(f"Data for {Month} successfully updated!")
    except Exception as e:
        st.warning(f"Unable to write.{e}")
    
    # Set the menu back to 'All Company' to refresh the display
    # st.session_state.selected_menu = menu
        
    # Optional: Show a success message
    st.success(f"Data updated for {Month}: Realisasi = {Realisasi}, Target = {Target}")

# Initialize session state for menu selection
if 'selected_menu' not in st.session_state:
    st.session_state.selected_menu = 'All Company'

# Sidebar menu
st.sidebar.image('GSPLogo.png', width=200)
menu_options = ['All Company', 'Accenture', 'IBM', 'Alibaba', 'F5', 'PaloAlto Networks', 'Cisco', 'Meta', 'Thales']
st.session_state.selected_menu = st.sidebar.selectbox(
    'Menu', 
    menu_options,
    index=menu_options.index(st.session_state.selected_menu)
)

if st.session_state.selected_menu == 'All Company':
    st.session_state.df = read_data(spreadsheet,"Sheet1")
    df_all_process = Analytics(st.session_state.df)
    # with st.sidebar.form("Update Form"):
    #     Month = st.selectbox("Month", st.session_state.df['Month'].tolist())
    #     Realisasi = st.number_input("Realisasi", value=0.0) 
    #     Target = st.number_input("Target", value=0.0) 
    #     submit = st.form_submit_button("Update Data")
    #     if submit:
    #         submit_update(df_all_process, 'All Company', spreadsheet, "Sheet1")
            
    show(df_all_process)
    df_style = df_all_process.style.format({
        'Realisasi': '{:.2f}', 
        'Target': '{:.2f}', 
        'Cumul_Realisasi': '{:.2f}', 
        'Cumul_Target': '{:.2f}', 
        'Monthly_Ach': '{:.2f}%', 
        'Quarterly_Ach': '{:.2f}%', 
        'Cumul_quarterly': '{:.2f}%', 
        'Cumul_vs_Yearly': '{:.2f}%'
    })

        # Display the styled dataframe
    st.dataframe(df_style, use_container_width=True)
    st.markdown(
    """
    <div style="text-align: center; font-size: 12px; color: grey;">
        <p>Realization & Target in IDR Billion.</p>
    </div>
    """,
    unsafe_allow_html=True
    )   
    show2(df_all_process)
    show3(df_all_process)
    show4(df_all_process)
    show5(df_all_process)
    show6(df_all_process)
    # st.session_state.selected_menu = 'All Company'

elif st.session_state.selected_menu == 'Accenture':
    st.session_state.df = read_data(spreadsheet,"Accenture")
    df_acc_process = Analytics(st.session_state.df)        
    with st.sidebar.form("Update Form"):
        Month = st.selectbox("Month", st.session_state.df['Month'].tolist())
        Realisasi = st.number_input("Realisasi", value=0.0) 
        Target = st.number_input("Target", value=0.0) 
        submit = st.form_submit_button("Update Data")
        if submit:
            submit_update(df_acc_process, 'Accenture', spreadsheet, "Accenture")
    
    st.session_state.df = read_data(spreadsheet,"Accenture")
    df_acc_process = Analytics(st.session_state.df)        
    show(df_acc_process)
    df_style = df_acc_process.style.format({
        'Realisasi': '{:.2f}', 
        'Target': '{:.2f}', 
        'Cumul_Realisasi': '{:.2f}', 
        'Cumul_Target': '{:.2f}', 
        'Monthly_Ach': '{:.2f}%', 
        'Quarterly_Ach': '{:.2f}%', 
        'Cumul_quarterly': '{:.2f}%', 
        'Cumul_vs_Yearly': '{:.2f}%'
    })

        # Display the styled dataframe
    st.dataframe(df_style, use_container_width=True)
    st.markdown(
    """
    <div style="text-align: center; font-size: 12px; color: grey;">
        <p>Realization & Target in IDR Billion.</p>
    </div>
    """,
    unsafe_allow_html=True
    )   
    show2(df_acc_process)
    show3(df_acc_process)
    show4(df_acc_process)
    show5(df_acc_process)
    show6(df_acc_process)
    # st.session_state.selected_menu = 'Accenture'

            
elif st.session_state.selected_menu == 'IBM':
    st.session_state.df = read_data(spreadsheet,"IBM")
    df_IBM_process = Analytics(st.session_state.df)
    with st.sidebar.form("Update Form"):
        Month = st.selectbox("Month", st.session_state.df['Month'].tolist())
        Realisasi = st.number_input("Realisasi", value=0.0) 
        Target = st.number_input("Target", value=0.0) 
        submit = st.form_submit_button("Update Data")
        if submit:
            submit_update(df_IBM_process, 'IBM', spreadsheet, "IBM")
            
    show(df_IBM_process)
    df_style = df_IBM_process.style.format({
        'Realisasi': '{:.2f}', 
        'Target': '{:.2f}', 
        'Cumul_Realisasi': '{:.2f}', 
        'Cumul_Target': '{:.2f}', 
        'Monthly_Ach': '{:.2f}%', 
        'Quarterly_Ach': '{:.2f}%', 
        'Cumul_quarterly': '{:.2f}%', 
        'Cumul_vs_Yearly': '{:.2f}%'
    })
    
    st.dataframe(df_style, use_container_width=True)
    st.markdown(
    """
    <div style="text-align: center; font-size: 12px; color: grey;">
        <p>Realization & Target in IDR Billion.</p>
    </div>
    """,
    unsafe_allow_html=True
    )   
    show2(df_IBM_process)
    show3(df_IBM_process)
    show4(df_IBM_process)
    show5(df_IBM_process)
    show6(df_IBM_process)
    # st.session_state.selected_menu = 'IBM'

            
elif st.session_state.selected_menu == 'Alibaba':
    st.session_state.df = read_data(spreadsheet,"Alibaba")
    df_Alb_process = Analytics(st.session_state.df)
    with st.sidebar.form("Update Form"):
        Month = st.selectbox("Month", st.session_state.df['Month'].tolist())
        Realisasi = st.number_input("Realisasi", value=0.0) 
        Target = st.number_input("Target", value=0.0) 
        submit = st.form_submit_button("Update Data")
        if submit:
            submit_update(df_Alb_process, 'Alibaba', spreadsheet, 'Alibaba')
            
    show(df_Alb_process)
    df_style = df_Alb_process.style.format({
        'Realisasi': '{:.2f}', 
        'Target': '{:.2f}', 
        'Cumul_Realisasi': '{:.2f}', 
        'Cumul_Target': '{:.2f}', 
        'Monthly_Ach': '{:.2f}%', 
        'Quarterly_Ach': '{:.2f}%', 
        'Cumul_quarterly': '{:.2f}%', 
        'Cumul_vs_Yearly': '{:.2f}%'
    })
    st.dataframe(df_style, use_container_width=True)
    st.markdown(
    """
    <div style="text-align: center; font-size: 12px; color: grey;">
        <p>Realization & Target in IDR Billion.</p>
    </div>
    """,
    unsafe_allow_html=True
    )   
    show2(df_Alb_process)
    show3(df_Alb_process)
    show4(df_Alb_process)
    show5(df_Alb_process)
    show6(df_Alb_process)
    # st.session_state.selected_menu = 'Alibaba'

            
elif st.session_state.selected_menu == 'F5':
    st.session_state.df = read_data(spreadsheet,"F5")
    df_f5_process = Analytics(st.session_state.df)
    with st.sidebar.form("Update Form"):
        Month = st.selectbox("Month", st.session_state.df['Month'].tolist())
        Realisasi = st.number_input("Realisasi", value=0.0) 
        Target = st.number_input("Target", value=0.0) 
        submit = st.form_submit_button("Update Data")
        if submit:
            submit_update(df_f5_process, 'F5', spreadsheet, 'F5')
    
    show(df_f5_process)
    df_style = df_f5_process.style.format({
        'Realisasi': '{:.2f}', 
        'Target': '{:.2f}', 
        'Cumul_Realisasi': '{:.2f}', 
        'Cumul_Target': '{:.2f}', 
        'Monthly_Ach': '{:.2f}%', 
        'Quarterly_Ach': '{:.2f}%', 
        'Cumul_quarterly': '{:.2f}%', 
        'Cumul_vs_Yearly': '{:.2f}%'
    })
    
    st.dataframe(df_style, use_container_width=True)
    st.markdown(
    """
    <div style="text-align: center; font-size: 12px; color: grey;">
        <p>Realization & Target in IDR Billion.</p>
    </div>
    """,
    unsafe_allow_html=True
    )   
    show2(df_f5_process)
    show3(df_f5_process)
    show4(df_f5_process)
    show5(df_f5_process)
    show6(df_f5_process)
    # st.session_state.selected_menu = 'F5'
    
elif st.session_state.selected_menu == 'PaloAlto Networks':
    st.session_state.df = read_data(spreadsheet,"Paloalto")
    df_pa_process = Analytics(st.session_state.df)
    with st.sidebar.form("Update Form"):
        Month = st.selectbox("Month", st.session_state.df['Month'].tolist())
        Realisasi = st.number_input("Realisasi", value=0.0) 
        Target = st.number_input("Target", value=0.0) 
        submit = st.form_submit_button("Update Data")
        if submit:
            submit_update(df_pa_process, 'Paloalto', spreadsheet, 'Paloalto')
    
    show(df_pa_process)
    df_style = df_pa_process.style.format({
        'Realisasi': '{:.2f}', 
        'Target': '{:.2f}', 
        'Cumul_Realisasi': '{:.2f}', 
        'Cumul_Target': '{:.2f}', 
        'Monthly_Ach': '{:.2f}%', 
        'Quarterly_Ach': '{:.2f}%', 
        'Cumul_quarterly': '{:.2f}%', 
        'Cumul_vs_Yearly': '{:.2f}%'
    })
    
    st.dataframe(df_style, use_container_width=True)
    st.markdown(
    """
    <div style="text-align: center; font-size: 12px; color: grey;">
        <p>Realization & Target in IDR Billion.</p>
    </div>
    """,
    unsafe_allow_html=True
    )   
    show2(df_pa_process)
    show3(df_pa_process)
    show4(df_pa_process)
    show5(df_pa_process)
    show6(df_pa_process)
    # st.session_state.selected_menu = 'PaloAlto Networks'
            
elif st.session_state.selected_menu == 'Cisco':
    st.session_state.df = read_data(spreadsheet,"Cisco")
    df_cisco_process = Analytics(st.session_state.df)
    with st.sidebar.form("Update Form"):
        Month = st.selectbox("Month", st.session_state.df['Month'].tolist())
        Realisasi = st.number_input("Realisasi", value=0.0) 
        Target = st.number_input("Target", value=0.0) 
        submit = st.form_submit_button("Update Data")
        if submit:
            submit_update(df_cisco_process, 'Cisco', spreadsheet, 'Cisco')
            
    show(df_cisco_process)
    df_style = df_cisco_process.style.format({
        'Realisasi': '{:.2f}', 
        'Target': '{:.2f}', 
        'Cumul_Realisasi': '{:.2f}', 
        'Cumul_Target': '{:.2f}', 
        'Monthly_Ach': '{:.2f}%', 
        'Quarterly_Ach': '{:.2f}%', 
        'Cumul_quarterly': '{:.2f}%', 
        'Cumul_vs_Yearly': '{:.2f}%'
    })
        
    st.dataframe(df_style, use_container_width=True)
    st.markdown(
    """
    <div style="text-align: center; font-size: 12px; color: grey;">
        <p>Realization & Target in IDR Billion.</p>
    </div>
    """,
    unsafe_allow_html=True
    )   
    show2(df_cisco_process)
    show3(df_cisco_process)
    show4(df_cisco_process)
    show5(df_cisco_process)
    show6(df_cisco_process)
    # st.session_state.selected_menu = 'Cisco'

elif st.session_state.selected_menu == 'Meta':
    st.session_state.df = read_data(spreadsheet,"Meta")
    df_mt_process = Analytics(st.session_state.df)
    with st.sidebar.form("Update Form"):
        Month = st.selectbox("Month", st.session_state.df['Month'].tolist())
        Realisasi = st.number_input("Realisasi", value=0.0) 
        Target = st.number_input("Target", value=0.0) 
        submit = st.form_submit_button("Update Data")
        if submit:
            submit_update(df_mt_process, 'Meta', spreadsheet, 'Meta')
            
    show(df_mt_process)
    df_style = df_mt_process.style.format({
        'Realisasi': '{:.2f}', 
        'Target': '{:.2f}', 
        'Cumul_Realisasi': '{:.2f}', 
        'Cumul_Target': '{:.2f}', 
        'Monthly_Ach': '{:.2f}%', 
        'Quarterly_Ach': '{:.2f}%', 
        'Cumul_quarterly': '{:.2f}%', 
        'Cumul_vs_Yearly': '{:.2f}%'
    })
        
    st.dataframe(df_style, use_container_width=True)
    st.markdown(
    """
    <div style="text-align: center; font-size: 12px; color: grey;">
        <p>Realization & Target in IDR Billion.</p>
    </div>
    """,
    unsafe_allow_html=True
    )   
    show2(df_mt_process)
    show3(df_mt_process)
    show4(df_mt_process)
    show5(df_mt_process)
    show6(df_mt_process)
    # st.session_state.selected_menu = 'Meta'
            
elif st.session_state.selected_menu == 'Thales':
    st.session_state.df = read_data(spreadsheet,"Thales")
    df_tl_process = Analytics(st.session_state.df)
    with st.sidebar.form("Update Form"):
        Month = st.selectbox("Month", st.session_state.df['Month'].tolist())
        Realisasi = st.number_input("Realisasi", value=0.0) 
        Target = st.number_input("Target", value=0.0) 
        submit = st.form_submit_button("Update Data")
        if submit:
            submit_update(df_tl_process, 'Thales', spreadsheet, 'Thales')
            
    show(df_tl_process)
    df_style = df_tl_process.style.format({
        'Realisasi': '{:.2f}', 
        'Target': '{:.2f}', 
        'Cumul_Realisasi': '{:.2f}', 
        'Cumul_Target': '{:.2f}', 
        'Monthly_Ach': '{:.2f}%', 
        'Quarterly_Ach': '{:.2f}%', 
        'Cumul_quarterly': '{:.2f}%', 
        'Cumul_vs_Yearly': '{:.2f}%'
    })
    
    st.dataframe(df_style, use_container_width=True)
    st.markdown(
    """
    <div style="text-align: center; font-size: 12px; color: grey;">
        <p>Realization & Target in IDR Billion.</p>
    </div>
    """,
    unsafe_allow_html=True
    )   
    show2(df_tl_process)
    show3(df_tl_process)
    show4(df_tl_process)
    show5(df_tl_process)
    show6(df_tl_process)
    # st.session_state.selected_menu = 'Thales'
            
        # df_style = df_acc.style.format({
        #         'Realisasi': '{:.2f}', 
        #         'Target': '{:.2f}', 
        #         'Cumul_Realisasi': '{:.2f}', 
        #         'Cumul_Target': '{:.2f}', 
        #         'Monthly_Ach': '{:.2f}%', 
        #         'Quarterly_Ach': '{:.2f}%', 
        #         'Cumul_quarterly': '{:.2f}%', 
        #         'Cumul_vs_Yearly': '{:.2f}%'
        #     })

            # Display the styled dataframe
            
