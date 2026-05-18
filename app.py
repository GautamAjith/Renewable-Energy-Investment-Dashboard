import streamlit as st
import pandas as pd
import plotly.express as px


st.set_page_config(
    page_title="Renewable Energy Investment Dashboard",
    layout="wide"
)

st.title("Renewable Energy Investment Dashboard")
st.write("Data source: World Bank World Development Indicators")
st.write(
    "This dashboard explores renewable energy patterns across countries using World Bank data. I built it to compare renewable energy use, electricity access, CO2 emissions, and GDP Per Capita in one place."
)


FILES = {
    "Renewable Energy Consumption (%)": "API_EG.FEC.RNEW.ZS_DS2_en_csv_v2_2939.csv",
    "Electricity Access (%)": "API_EG.ELC.ACCS.ZS_DS2_en_csv_v2_127016.csv",
    "CO2 Emissions per Capita": "API_EN.GHG.CO2.PC.CE.AR5_DS2_en_csv_v2_115509.csv",
    "GDP per Capita": "API_NY.GDP.PCAP.CD_DS2_en_csv_v2_121663.csv"
}

COUNTRY_METADATA_FILE = "Metadata_Country_API_EG.FEC.RNEW.ZS_DS2_en_csv_v2_2939.csv"


@st.cache_data
def read_world_bank_csv(file_name, variable_name):
    df = pd.read_csv(file_name, skiprows=4)

    df = df.drop(columns=["Indicator Name", "Indicator Code"], errors="ignore")

    year_columns = []

    for col in df.columns:
        if col.isdigit():
            year_columns.append(col)

    df_long = df.melt(
        id_vars=["Country Name", "Country Code"],
        value_vars=year_columns,
        var_name="year",
        value_name=variable_name
    )

    df_long = df_long.rename(
        columns={
            "Country Name": "country",
            "Country Code": "iso3"
        }
    )

    df_long["year"] = df_long["year"].astype(int)

    return df_long


@st.cache_data
def load_data():
    all_data = []

    for variable_name, file_name in FILES.items():
        temp = read_world_bank_csv(file_name, variable_name)
        all_data.append(temp)

    df = all_data[0]

    for temp in all_data[1:]:
        df = df.merge(
            temp,
            on=["country", "iso3", "year"],
            how="outer"
        )

    metadata = pd.read_csv(COUNTRY_METADATA_FILE)

    metadata = metadata[[
        "Country Code",
        "Region",
        "IncomeGroup"
    ]]

    metadata = metadata.rename(
        columns={
            "Country Code": "iso3",
            "IncomeGroup": "Income Group"
        }
    )

    df = df.merge(metadata, on="iso3", how="left")

    df = df[df["Region"].notna()]
    df = df[df["Income Group"].notna()]

    df = df.sort_values(["country", "year"])

    numeric_columns = [
        "Renewable Energy Consumption (%)",
        "Electricity Access (%)",
        "CO2 Emissions per Capita",
        "GDP per Capita"
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fill missing values within each country using nearby years.
    for col in numeric_columns:
        df[col] = df.groupby("country")[col].transform(
            lambda x: x.interpolate(limit_direction="both")
        )

    return df


df = load_data()


st.sidebar.header("Filters")

available_years = sorted(df["year"].dropna().unique())

selected_year = st.sidebar.slider(
    "Select year",
    min_value=int(min(available_years)),
    max_value=int(max(available_years)),
    value=2022
)

regions = sorted(df["Region"].dropna().unique())

selected_regions = st.sidebar.multiselect(
    "Select region",
    regions,
    default=regions
)

filtered_by_region = df[df["Region"].isin(selected_regions)]

countries = sorted(filtered_by_region["country"].dropna().unique())

default_countries = [
    "India",
    "United States",
    "China",
    "Russia",
    "United Kingdom",
    "United Arab Emirates"
]

default_countries = [
    country for country in default_countries
    if country in countries
]

selected_countries = st.sidebar.multiselect(
    "Select countries for trend charts",
    countries,
    default=default_countries
)

df_year = filtered_by_region[filtered_by_region["year"] == selected_year]

df_selected_countries = filtered_by_region[
    filtered_by_region["country"].isin(selected_countries)
]


st.subheader(f"Global Overview for {selected_year}")

map_data = df_year.dropna(subset=["Renewable Energy Consumption (%)"])

fig_map = px.choropleth(
    map_data,
    locations="iso3",
    color="Renewable Energy Consumption (%)",
    hover_name="country",
    hover_data={
        "Region": True,
        "Income Group": True,
        "Renewable Energy Consumption (%)": ":.2f",
        "Electricity Access (%)": ":.2f",
        "CO2 Emissions per Capita": ":.2f",
        "GDP per Capita": ":,.2f",
        "iso3": False
    },
    color_continuous_scale="Greens",
    title="Renewable Energy Consumption by Country"
)

st.plotly_chart(fig_map, use_container_width=True)


col1, col2, col3 = st.columns(3)

avg_renewable = df_year["Renewable Energy Consumption (%)"].mean()
avg_electricity = df_year["Electricity Access (%)"].mean()
avg_co2 = df_year["CO2 Emissions per Capita"].mean()

with col1:
    st.metric(
        "Average Renewable Energy Consumption",
        f"{avg_renewable:.2f}%"
    )

with col2:
    st.metric(
        "Average Electricity Access",
        f"{avg_electricity:.2f}%"
    )

with col3:
    st.metric(
        "Average CO2 Emissions per Capita",
        f"{avg_co2:.2f}"
    )


col4, col5 = st.columns(2)

with col4:
    st.subheader("Renewable Energy Trend")

    renewable_trend = df_selected_countries.dropna(
        subset=["Renewable Energy Consumption (%)"]
    )

    fig_renewable = px.line(
        renewable_trend,
        x="year",
        y="Renewable Energy Consumption (%)",
        color="country",
        markers=True,
        title="Renewable Energy Consumption Over Time"
    )

    st.plotly_chart(fig_renewable, use_container_width=True)


with col5:
    st.subheader("CO2 Emissions Trend")

    co2_trend = df_selected_countries.dropna(
        subset=["CO2 Emissions per Capita"]
    )

    fig_co2 = px.line(
        co2_trend,
        x="year",
        y="CO2 Emissions per Capita",
        color="country",
        markers=True,
        title="CO2 Emissions per Capita Over Time"
    )

    st.plotly_chart(fig_co2, use_container_width=True)


st.subheader("Investment Opportunity")

scatter_data = df_year.dropna(
    subset=[
        "Renewable Energy Consumption (%)",
        "Electricity Access (%)",
        "GDP per Capita",
        "CO2 Emissions per Capita"
    ]
)

fig_scatter = px.scatter(
    scatter_data,
    x="GDP per Capita",
    y="Renewable Energy Consumption (%)",
    size="Electricity Access (%)",
    color="CO2 Emissions per Capita",
    hover_name="country",
    hover_data={
        "Region": True,
        "Income Group": True,
        "GDP per Capita": ":,.2f",
        "Electricity Access (%)": ":.2f",
        "CO2 Emissions per Capita": ":.2f",
        "Renewable Energy Consumption (%)": ":.2f"
    },
    log_x=True,
    title="Renewable Energy, GDP per Capita, Electricity Access, and CO2 Emissions",
    labels={
        "GDP per Capita": "GDP per Capita, current US$",
        "Renewable Energy Consumption (%)": "Renewable Energy Consumption (%)",
        "Electricity Access (%)": "Electricity Access (%)",
        "CO2 Emissions per Capita": "CO2 Emissions per Capita"
    }
)

st.plotly_chart(fig_scatter, use_container_width=True)


st.subheader("Top Renewable Energy Countries")

top_renewable = df_year.dropna(
    subset=["Renewable Energy Consumption (%)"]
).sort_values(
    "Renewable Energy Consumption (%)",
    ascending=False
).head(15)

fig_bar = px.bar(
    top_renewable,
    x="country",
    y="Renewable Energy Consumption (%)",
    color="Region",
    title=f"Top 15 Countries by Renewable Energy Consumption in {selected_year}"
)

st.plotly_chart(fig_bar, use_container_width=True)


st.subheader("Country Data Table")

table_data = df_year[[
    "country",
    "iso3",
    "Region",
    "Income Group",
    "year",
    "Renewable Energy Consumption (%)",
    "Electricity Access (%)",
    "CO2 Emissions per Capita",
    "GDP per Capita"
]].sort_values("country")

st.dataframe(table_data, use_container_width=True)


csv = table_data.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download filtered data as CSV",
    data=csv,
    file_name=f"world_bank_renewable_energy_dashboard_{selected_year}.csv",
    mime="text/csv"
)
