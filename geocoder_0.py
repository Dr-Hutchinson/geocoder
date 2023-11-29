import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import base64

# Initialize session state
if 'df_geocoded' not in st.session_state:
    st.session_state.df_geocoded = None

if 'df_original' not in st.session_state:
    st.session_state.df_original = None

if 'editing_done' not in st.session_state:
    st.session_state.editing_done = False

# Geocoding function
def geocode_locations(df, location_column='Location'):
    geolocator = Nominatim(user_agent="your_user_agent")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=2)

    latitudes = []
    longitudes = []

    for location in df[location_column]:
        try:
            location_point = geocode(location)
            latitudes.append(location_point.latitude)
            longitudes.append(location_point.longitude)
        except AttributeError:
            latitudes.append(None)
            longitudes.append(None)

    df['latitude_geocoded'] = latitudes
    df['longitude_geocoded'] = longitudes

    return df

# Convert DataFrame to CSV for download
@st.cache_data
def convert_df(df):
    return df.to_csv().encode('utf-8')

# Streamlit app
st.title('WWII U.S. Military Base Geocoder')

uploaded_file = st.file_uploader("Choose an Excel file", type=['xlsx', 'csv'])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    num_rows = len(df)
    min_delay_seconds = 2
    estimated_time = num_rows * min_delay_seconds
    estimated_minutes, estimated_seconds = divmod(estimated_time, 60)
    st.write(f"Number of Rows: {num_rows}")
    st.write(f"Estimated time to geocode: {estimated_minutes} minutes and {estimated_seconds} seconds")

    columns_of_interest = ['Military Base', 'Location', 'State', 'Subdescription', 'Image Number', 'Branch']
    df = df[columns_of_interest]
    df['Follow Up'] = False

    proceed = st.button("Proceed with Geocoding")

    if proceed and not st.session_state.editing_done:
        st.session_state.df_original = df
        st.session_state.editing_done = True
        st.session_state.df_geocoded = geocode_locations(df)
        st.session_state.df_geocoded.dropna(inplace=True)
        duplicate_geo = st.session_state.df_geocoded.duplicated(subset=['latitude_geocoded', 'longitude_geocoded'], keep=False)
        st.session_state.df_geocoded.loc[duplicate_geo, 'Follow Up'] = True

# Visualization of geocoding data
# Visualization of geocoding data
if st.session_state.df_geocoded is not None:
    with st.expander("Map showing geocoded locations.", expanded=True):

        # Initialize view state based on the average latitude and longitude from the geocoded DataFrame
        view_state = pdk.ViewState(
            latitude=st.session_state.df_geocoded['latitude_geocoded'].mean(),
            longitude=st.session_state.df_geocoded['longitude_geocoded'].mean(),
            zoom=1
        )

        # Prepare data for mapping
        data = st.session_state.df_geocoded.copy()

        # Debugging Element
        #st.write("Data DataFrame: ", data.head())

        # Let the user toggle between map styles first, as it doesn't affect the DataFrame
        #is_satellite = st.checkbox('Show satellite view', value=True)
        #map_style = 'mapbox://styles/mapbox/satellite-v9' if is_satellite else 'mapbox://styles/mapbox/streets-v11'

        # Add tooltip content (replace this with appropriate tooltip content from your DataFrame)
        data_reset_index = data.reset_index()

        tooltips = []
        for idx, row in data_reset_index.iterrows():
            tooltip = f"""
                <div style='word-wrap: break-word; width: 300px;'>
                    <br><b>Row Number:</b> {row['index']}
                    <br><b>Military Base:</b> {row['Military Base']}
                    <br><b>Location:</b> {row['Location']}
                    <br><b>State:</b> {row['State']}
                    <br><b>Subdescription:</b> {row['Subdescription']}
                    <br><b>Image Number:</b> {row['Image Number']}
                    <br><b>Branch:</b> {row['Branch']}
                </div>"""

            tooltips.append(tooltip)
            # debugging element
            #st.write(f"Processing Row: {row['index']}, Tooltip: {tooltip}")  # Debugging: Print the current row

        data['tooltip'] = tooltips

        # Check for NaNs in the DataFrame
        nan_cols = data.isna().any()

        # Debugging Elements
        #st.write(f"Columns with NaNs: {nan_cols}")  # Debugging: Print columns that contain NaNs
        #st.write("Data Reset Index DataFrame: ", data_reset_index.head())
        #st.write("Tooltip Content: ", data['tooltip'].head())

        # Define the icon data
        icon_data = {"url":"https://img.icons8.com/plasticine/100/000000/marker.png", "width":128, "height":128, "anchorY":128}
        data["icon"] = [icon_data for _ in range(len(data))]

        # Define the layer
        layer = pdk.Layer(
            type="IconLayer",
            data=data,
            get_icon="icon",
            get_size=4,
            size_scale=15,
            get_position=["longitude_geocoded", "latitude_geocoded"],
            pickable=True,
        )

        # Let the user toggle between map styles
        is_satellite = st.checkbox('Show satellite view', value=True)
        if is_satellite:
            map_style = 'mapbox://styles/mapbox/satellite-v9'
        else:
            map_style = 'mapbox://styles/mapbox/streets-v11'

        tooltip={
            "html": "{tooltip}",
            "style": {
                "backgroundColor": "steelblue",
                "color": "white"
            }
        }

        # Define and display the map
        r = pdk.Deck(
            map_style=map_style,
            initial_view_state=view_state,
            layers=[layer],
            tooltip=tooltip
        )
        st.pydeck_chart(r)

# Editable dataframe for follow-up
with st.expander("Review and Mark for Follow Up:", expanded=True):
    if st.session_state.df_original is not None:
        edited_follow_up_df = st.data_editor(
            st.session_state.df_original,
            num_rows="dynamic",
            key="follow_up_data_editor_2"
        )

        if st.button("Save Changes"):
            st.session_state.df_original = edited_follow_up_df

# Download button for the CSV file
if st.session_state.df_original is not None:
    csv = convert_df(st.session_state.df_original)
    st.download_button(
        label="Download data with Follow Ups",
        data=csv,
        file_name='data_with_follow_ups.csv',
        mime='text/csv'
    )
