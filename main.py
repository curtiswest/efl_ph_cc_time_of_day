import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.header('Occupancy model for PH traffic')

@st.cache_data
def data():
    df = pd.read_csv(r"./seasonal_ph_sales.csv")
    df = df.rename(columns={'wager_datetime': 'datetime'})
    df['datetime'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d %H:%M:%S')

    df['day_of_week'] = df['datetime'].dt.day_name()
    df['is_weekend'] = df['day_of_week'].isin(['Saturday', 'Sunday'])
    df['time'] = df['datetime'].dt.time
    df['date'] = df['datetime'].dt.date

    return df

time_at_house = st.slider('Est. time spent at house (mins)', min_value=10, max_value=60, step=10, value=30,
                          format='%d mins', help='How long do you think people will spend at the house?')
progress_pct_lower, progress_pct_upper = st.slider('Draw phase (percentage)', min_value=0, max_value=100, step=1, value=(0, 100),
                                                   format='%d%%', help='Use this to view only the final 25% (busiest) part of the draw.')

fig_data = data()
num_draws = fig_data.draw_no.nunique()

from plotly.subplots import make_subplots
col1, col2 = st.columns(2, gap='small')

for idx, draw_no in enumerate(fig_data.draw_no.unique()):
    fig = go.Figure()
    draw_df = fig_data[fig_data.draw_no == draw_no].copy()

    first_date = draw_df.date.min()
    last_date = draw_df.date.max()

    cutoff_date_lower = first_date + pd.Timedelta(days=progress_pct_lower/100 * (last_date - first_date).days)
    cutoff_date_upper = first_date + pd.Timedelta(days=progress_pct_upper/100 * (last_date - first_date).days)

    weekend = draw_df.copy()
    weekend = weekend[weekend.date <= cutoff_date_upper]
    weekend = weekend[weekend.date >= cutoff_date_lower]
    weekend = weekend[weekend.is_weekend]
    # group weekend by 30 minutes
    weekend['time_rounded'] = weekend['datetime'].dt.round(f'{time_at_house}min')
    weekend['time'] = weekend['time_rounded'].dt.time

    weekend = weekend.groupby(['date', 'time'])[['customer_id']].count().reset_index()
    weekend = weekend.rename(columns={'customer_id': 'sales'})

    num_unique_dates = len(weekend.date.unique())
    color = '#000000'

    # get quartiles of sales
    q1 = weekend.sales.quantile(0.25)
    q2 = weekend.sales.quantile(0.5)
    q3 = weekend.sales.quantile(0.75)
    q4 = weekend.sales.quantile(1)
    pct_90 = weekend.sales.quantile(0.9)
    pct_95 = weekend.sales.quantile(0.95)
    pct_100 = weekend.sales.quantile(1)
    print(f'Draw {draw_no} quartiles: {q1}, {q2}, {q3}, {q4}')

    for date in weekend.date.unique():
        # date pct between num_unique_dates
        date_pct = (weekend.date.unique().tolist().index(date) + 1) / num_unique_dates
        date_df = weekend[weekend.date == date]
        fig.add_trace(
            go.Scatter(
                x=date_df.time, y=date_df.sales, name=f'{date}', line=dict(color=color, width=1),
                opacity=date_pct
            ),
        )
    fig.add_hline(y=pct_90, line_dash="dash", line_color=color, opacity=1, annotation_text=f'90th Percentile: {int(pct_90)}')
    fig.add_hline(y=pct_95, line_dash="dash", line_color=color, opacity=1, annotation_text=f'95th Percentile: {int(pct_95)}')
    fig.add_hline(y=pct_100, line_dash="dash", line_color=color, opacity=1, annotation_text=f'100th Percentile: {int(pct_100)}')


    fig.update_layout(
        title=f'# of Sales by Time of Day - Draw {draw_no}',
    )

    if idx % 2 == 0:
        col1.write(fig)
    else:
        col2.write(fig)

