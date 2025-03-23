from pathlib import Path
import pandas as pd

pd.options.mode.copy_on_write = True

app_dir = Path(__file__).parent
grants = pd.read_csv(app_dir / "LC_grants.csv", delimiter=",")

# add coordinates as a list of lon, lat for maplibre

grants["coordinates"] = grants[["lon","lat"]].values.tolist()

# calculate the total of all grants
grant_total = grants["Amnt_awa"].sum()

# grant types and sub-categories
grant_areas = {
    "AA":"All",
    "Adv": "Advice",
    "Art": "Arts",
    "Aware": "Awareness",
    "Core": "Core funding",
    "Med":"Medical",
    "Psychol":"Psychological",
    "Social":"Social care",
    "Well":"Wellbeing"
    
}

# create grant range for filters
grant_range = (grants["Amnt_awa"].min(),grants["Amnt_awa"].max())

# maplibre specifications
BOUNDS = (-8.92242886, 43.30508298, 13.76496714, 59.87668996)
# set color definitions for map markers
def get_color(grant_type: str) -> str:
    color = "darkblue"
    if grant_type == "Social care":
        color = "#292f56"
    elif grant_type == "Psychological":
        color = "#21416d"
    elif grant_type == "Medical":
        color ='#005483'
    elif grant_type == "Arts":
        color = '#006794'
    elif grant_type == "Awareness":
        color = '#007a9a'
    elif grant_type == "Advice":
        color = '#008da1'
    elif grant_type == "Communication":
        color = '#00a1a4'
    elif grant_type == "Wellbeing":
        color = "#00b5a3"
    elif grant_type == "Social research":
        color = "#00ca9a"
    elif grant_type == "Core funding":
        color = '#36dc8d'
    elif grant_type == "Rehabilitation":
        color = '#76ec7e'
    elif grant_type == "Epidemiology":
        color = '#acfa70'
    
    return color

