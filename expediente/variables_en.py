"""Versión en inglés del catálogo de variables (ver `variables.py`, que es la fuente de verdad).

Cada entrada repite, por código de variable, los textos que cambian con el idioma. Las
unidades, los temas, las fuentes y las resoluciones se traducen por tabla (`FRASES`).
"""

from __future__ import annotations

_MERRA = "MERRA-2, field {} of the {} collection."
_POWER = "Computed by NASA POWER from {} of MERRA-2."
_AVISO_EXT = ("The extremes of a reanalysis of about 50 km are smoother than those of a weather station: "
              "they are useful to assess the trend, not the exact value of an event.")


def _ext(campo: str) -> str:
    return (f"Computed by this project from the daily field {campo} of MERRA-2. One value per year; only "
            f"years with at least 360 days of data count.")


VARIABLES_EN: dict[str, dict[str, str]] = {
    "T2M": dict(
        nombre="Air temperature",
        definicion="How warm the air is 2 metres above the ground, the height at which we live.",
        tecnica="Mean (dry-bulb) air temperature at 2 m above the surface. Monthly mean of the hourly values.",
        producto=_MERRA.format("T2M", "tavg1_2d_slv_Nx surface"),
        relevancia="It is the basic indicator of global warming and shapes health, agriculture and energy demand."),
    "T2M_MAX": dict(
        nombre="Maximum temperature of the month",
        definicion="The hottest moment of each month: the highest temperature that was reached.",
        tecnica="Maximum of the hourly air temperature at 2 m within the month.",
        producto=_POWER.format("the hourly T2M field"),
        relevancia="Heat extremes drive heat waves, thermal stress and wildfire risk."),
    "T2M_MIN": dict(
        nombre="Minimum temperature of the month",
        definicion="The coldest moment of each month: the lowest temperature that was reached.",
        tecnica="Minimum of the hourly air temperature at 2 m within the month.",
        producto=_POWER.format("the hourly T2M field"),
        relevancia="Minimum temperatures control frost and the night-time recovery of people and crops."),
    "T2M_RANGE": dict(
        nombre="Diurnal temperature range",
        definicion="How many degrees the temperature changes between the warmest and the coldest part of a typical day.",
        tecnica="Difference between the maximum and minimum hourly air temperature at 2 m on each day, averaged over "
                "the month (diurnal temperature range).",
        producto=_POWER.format("the hourly T2M field"),
        relevancia="It responds to changes in cloud cover, humidity and land use: it shrinks when nights warm more than days."),
    "TS": dict(
        nombre="Surface temperature",
        definicion="The temperature of the planet's \"skin\": the ground, the pavement or the water, not the air.",
        tecnica="Mean radiative temperature of the Earth's surface (skin temperature).",
        producto=_MERRA.format("TS", "tavg1_2d_slv_Nx"),
        relevancia="It governs the exchange of heat between the surface and the atmosphere and reveals local effects "
                   "such as the urban heat island."),
    "FROST_DAYS": dict(
        nombre="Frost days",
        definicion="How many days of the month had frost: the air cooled enough to form ice crystals.",
        tecnica="Number of days in the month on which the 2 m temperature drops to the dew point and both fall below 0 °C.",
        producto=_POWER.format("the T2M and T2MDEW fields"),
        relevancia="It marks the length of the growing season and the survival of pests and cold-sensitive crops."),
    "CDD18_3": dict(
        nombre="Cooling degree days",
        definicion="It adds up how much heat there is \"in excess\" above 18.3 °C. The higher it is, the more air "
                   "conditioning is needed.",
        tecnica="Monthly accumulation of the degrees by which the daily mean temperature exceeds the 18.3 °C (65 °F) "
                "threshold. Standard indicator of cooling demand.",
        producto=_POWER.format("the 2 m temperature"),
        relevancia="It translates warming into electricity demand for cooling buildings."),
    "HDD18_3": dict(
        nombre="Heating degree days",
        definicion="It adds up how much cold there is below 18.3 °C. The higher it is, the more heating is needed.",
        tecnica="Monthly accumulation of the degrees by which the daily mean temperature falls below the 18.3 °C "
                "(65 °F) threshold. Standard indicator of heating demand.",
        producto=_POWER.format("the 2 m temperature"),
        relevancia="It translates climate into energy demand for heating; it decreases when winters become milder."),
    "PRECTOTCORR": dict(
        nombre="Precipitation (reanalysis)",
        definicion="Rain and snow that fall on average each day, according to NASA's model.",
        tecnica="Mean total surface precipitation of the MERRA-2 reanalysis, bias-corrected with rain-gauge and "
                "satellite observations.",
        producto=_MERRA.format("PRECTOTCORR", "tavg1_2d_flx_Nx flux"),
        relevancia="It is the main input of the water cycle: rivers, aquifers, crops and droughts depend on it."),
    "PRECSNOLAND": dict(
        nombre="Snowfall",
        definicion="The part of precipitation that falls as snow.",
        tecnica="Precipitation in the form of snow over land, in liquid water equivalent.",
        producto=_MERRA.format("PRECSNOLAND", "tavg1_2d_lnd_Nx land surface"),
        relevancia="Snow stores water in winter and releases it in spring; its changes alter river flow."),
    "SNODP": dict(
        nombre="Snow depth",
        definicion="Thickness of the layer of snow accumulated on the ground.",
        tecnica="Thickness of the snowpack over land.",
        producto=_MERRA.format("SNODP", "tavg1_2d_lnd_Nx"),
        relevancia="The snowpack reflects sunlight and is a water reserve; its reduction amplifies warming."),
    "GWETTOP": dict(
        nombre="Surface soil wetness",
        definicion="How wet the top 5 cm of soil are: 0 is completely dry and 1 is soaked.",
        tecnica="Degree of water saturation in the top 5 cm of soil: 0 corresponds to completely dry soil and 1 to "
                "saturated soil.",
        producto=_MERRA.format("GWETTOP", "tavg1_2d_lnd_Nx"),
        relevancia="It controls how much rain infiltrates or runs off and how much of the Sun's energy is spent "
                   "evaporating water."),
    "GWETROOT": dict(
        nombre="Root-zone soil wetness",
        definicion="How wet the first metre of soil is, where plants drink from: 0 is completely dry and 1 is soaked.",
        tecnica="Degree of water saturation in the root zone, roughly the first metre of soil: 0 corresponds to "
                "completely dry soil and 1 to saturated soil.",
        producto=_MERRA.format("GWETROOT", "tavg1_2d_lnd_Nx"),
        relevancia="It is the water available to plants: its decline anticipates agricultural drought."),
    "EVLAND": dict(
        nombre="Evaporation",
        definicion="Water that passes from the soil and from plants into the air.",
        tecnica="Evaporation flux from the land surface (soil, vegetation and snow).",
        producto=_MERRA.format("EVLAND", "tavg1_2d_lnd_Nx"),
        relevancia="It returns water to the atmosphere and cools the surface; it links the water cycle with the "
                   "energy cycle."),
    "QV2M": dict(
        nombre="Specific humidity",
        definicion="How many grams of invisible water (vapour) there are in each kilogram of air.",
        tecnica="Ratio of the mass of water vapour to the total mass of air at 2 m.",
        producto=_MERRA.format("QV2M", "tavg1_2d_slv_Nx"),
        relevancia="Warmer air can hold more vapour, which strengthens the greenhouse effect and extreme rainfall."),
    "RH2M": dict(
        nombre="Relative humidity",
        definicion="How close the air is to being saturated with vapour: at 100 % fog or dew forms.",
        tecnica="Ratio of the vapour pressure to the saturation vapour pressure over a flat surface of pure water, "
                "at 2 m, in per cent.",
        producto=_POWER.format("temperature, humidity and pressure"),
        relevancia="It influences thermal comfort, wildfire risk and the formation of clouds and fog."),
    "T2MDEW": dict(
        nombre="Dew point",
        definicion="The temperature to which the air would have to cool to form dew. It rises when the air carries "
                   "more moisture.",
        tecnica="Dew or frost point temperature at 2 m above the surface.",
        producto=_MERRA.format("T2MDEW", "tavg1_2d_slv_Nx"),
        relevancia="It measures the actual moisture content of the air and is key to assessing humid heat stress."),
    "TQV": dict(
        nombre="Total precipitable water",
        definicion="All the water in the form of vapour above the place, from the ground up to space.",
        tecnica="Total water vapour contained in a vertical column of unit cross-section, from the surface to the "
                "top of the atmosphere.",
        producto=_MERRA.format("TQV", "tavg1_2d_slv_Nx"),
        relevancia="It is the fuel of precipitation, and water vapour is the main natural greenhouse gas."),
    "WS10M": dict(
        nombre="Wind speed at 10 m",
        definicion="Average wind speed at a height of 10 metres.",
        tecnica="Mean wind speed at 10 m above the surface.",
        producto=_POWER.format("the U10M and V10M components"),
        relevancia="Wind carries heat and moisture, drives evaporation and determines wind-power potential."),
    "WS50M": dict(
        nombre="Wind speed at 50 m",
        definicion="Average wind speed at 50 metres, the height of a small wind turbine.",
        tecnica="Mean wind speed at 50 m above the surface.",
        producto=_POWER.format("the U50M and V50M components"),
        relevancia="It is the reference for assessing the wind resource at turbine height."),
    "PS": dict(
        nombre="Surface pressure",
        definicion="The weight of the air above the place.",
        tecnica="Mean atmospheric pressure at the level of the Earth's surface.",
        producto=_MERRA.format("PS", "tavg1_2d_slv_Nx"),
        relevancia="Its variations define weather systems: highs and lows, winds and storms."),
    "TO3": dict(
        nombre="Total column ozone",
        definicion="Total amount of ozone above the place. The ozone layer protects us from ultraviolet rays.",
        tecnica="Total amount of ozone in a vertical column from the surface to the top of the atmosphere.",
        producto=_MERRA.format("TO3", "tavg1_2d_slv_Nx"),
        relevancia="The ozone layer absorbs harmful ultraviolet radiation; its recovery has been monitored since "
                   "the Montreal Protocol."),
    "TROPPB": dict(
        nombre="Tropopause pressure",
        definicion="The tropopause is the \"ceiling\" of the layer of air where weather happens. If its pressure "
                   "drops, that ceiling is rising.",
        tecnica="Pressure at the tropopause according to the blended estimate of MERRA-2. A drop in pressure "
                "indicates a higher tropopause.",
        producto=_MERRA.format("TROPPB", "tavg1_2d_slv_Nx"),
        relevancia="The height of the tropopause responds to the warming of the troposphere and is one of the "
                   "fingerprints of climate change."),
    "TROPT": dict(
        nombre="Tropopause temperature",
        definicion="How cold the \"ceiling\" of the layer of air where weather happens is, some 10 to 17 km up.",
        tecnica="Air temperature at the tropopause, the boundary between the troposphere and the stratosphere. It "
                "describes a high level of the atmosphere, not the surface.",
        producto=_MERRA.format("TROPT", "tavg1_2d_slv_Nx"),
        relevancia="The tropopause is a high level of the atmosphere: its temperature responds to climate change "
                   "differently from the surface."),
    "SLP": dict(
        nombre="Sea-level pressure",
        definicion="Air pressure adjusted as if the place were at sea level, so that sites at different altitudes "
                   "can be compared.",
        tecnica="Atmospheric pressure reduced to mean sea level.",
        producto=_MERRA.format("SLP", "tavg1_2d_slv_Nx"),
        relevancia="Its sustained changes reveal shifts in the high- and low-pressure systems that organise climate."),
    "AOD_55": dict(
        nombre="Aerosol optical depth (model)",
        definicion="How much dust, smoke and pollution block the light. It is measured with an index called AOD: "
                   "near 0 the air is very clean; above 0.4 it already looks hazy.",
        tecnica="Aerosol optical depth at 0.55 µm in the vertical: it measures how much radiation suspended "
                "particles remove from an incident beam. Dimensionless.",
        producto="CERES SYN1deg, whose aerosol field comes from the MATCH transport model with assimilation of "
                 "MODIS observations.",
        aviso="It is a field from a model that assimilates satellite observations, not a direct measurement. The "
              "SYN1deg product may have discontinuities when the satellites that feed it change.",
        relevancia="Aerosols affect health, cool the surface by reflecting sunlight and modify clouds."),
    "GPM_LLUVIA": dict(
        nombre="Precipitation (GPM satellite)",
        definicion="Rain and snow observed by a constellation of satellites with radars and microwave sensors, "
                   "refined with rain gauges on the ground.",
        tecnica="Monthly mean precipitation from the IMERG algorithm (Final Run), which combines the microwave and "
                "infrared sensors of the GPM constellation and is calibrated with rain gauges. Converted from mm/h "
                "to mm/day.",
        producto="GPM IMERG Final V07 monthly (3IMERGM), band precipitation; Google Earth Engine collection "
                 "NASA/GPM_L3/IMERG_MONTHLY_V07.",
        relevancia="It is an observation of precipitation independent of models, available even where there are no "
                   "rain gauges."),
    "GRACE_AGUA": dict(
        nombre="Terrestrial water storage (GRACE)",
        definicion="All the water stored at the place: aquifers, soil, rivers and snow. Two twin satellites "
                   "\"weigh\" it by measuring how gravity changes. It is expressed in centimetres of water above or "
                   "below the 2004 to 2009 average.",
        tecnica="Anomaly of total terrestrial water storage, in liquid water equivalent thickness relative to the "
                "2004–2009 mean, estimated from variations in the gravity field (JPL mascon solution with CRI filter).",
        producto="JPL GRACE/GRACE-FO Mascon RL06.3 v04 CRI, band lwe_thickness; Google Earth Engine collection "
                 "NASA/GRACE/MASS_GRIDS_V04/MASCON_CRI.",
        aviso="The real resolution is about 300 km: it cannot tell a city from its surroundings. Data are missing "
              "from mid-2017 to mid-2018, between the GRACE and GRACE-FO missions.",
        relevancia="It is the only satellite measurement of the total water stored in a region, groundwater included."),
    "MODIS_NDVI": dict(
        nombre="NDVI vegetation index (MODIS)",
        definicion="How green and lush the surface looks from the satellite. It is measured with an index called "
                   "NDVI: near 0 is bare soil; near 1, dense rainforest.",
        tecnica="Normalized Difference Vegetation Index: (NIR − red) / (NIR + red), computed from MODIS surface "
                "reflectances. Monthly composite.",
        producto="MODIS/Terra MOD13A3 V061, band NDVI; Google Earth Engine collection MODIS/061/MOD13A3.",
        relevancia="It reflects the amount and health of vegetation: it responds to droughts, deforestation, "
                   "irrigation and land-use change."),
    "MODIS_EVI": dict(
        nombre="Enhanced vegetation index EVI (MODIS)",
        definicion="Another way of measuring how green the surface is. It discriminates better than NDVI in "
                   "rainforests and very dense forests.",
        tecnica="Enhanced Vegetation Index: it uses the red, near-infrared and blue bands to reduce the effect of "
                "the atmosphere and the soil, and does not saturate over dense vegetation. Monthly composite.",
        producto="MODIS/Terra MOD13A3 V061, band EVI; Google Earth Engine collection MODIS/061/MOD13A3.",
        relevancia="It complements NDVI where the latter saturates; it allows a second index to confirm whether "
                   "vegetation is changing."),
    "MODIS_AOD": dict(
        nombre="Aerosol optical depth (MODIS)",
        definicion="How much dust, smoke and pollution block the light, measured directly by the satellite.",
        tecnica="Aerosol optical depth at 0.55 µm over land and ocean, monthly mean of the retrievals of the MODIS "
                "instrument. Dimensionless.",
        producto="MODIS/Terra MOD08_M3 V061, field Aerosol_Optical_Depth_Land_Ocean_Mean_Mean; Google Earth Engine "
                 "collection MODIS/061/MOD08_M3.",
        relevancia="It is a direct observation of aerosols, which affect health, the sunlight reaching the ground "
                   "and clouds."),
    "MODIS_NUBES": dict(
        nombre="Cloud cover (MODIS)",
        definicion="What part of the sky is covered by clouds, as seen from the satellite.",
        tecnica="Fraction of the area covered by clouds according to the MODIS cloud mask, monthly mean, in per cent.",
        producto="MODIS/Terra MOD08_M3 V061, field Cloud_Fraction_Mean_Mean; Google Earth Engine collection "
                 "MODIS/061/MOD08_M3.",
        relevancia="Clouds regulate how much of the Sun's energy comes in and how much goes out: they are the "
                   "largest uncertainty in climate."),
    "OMI_OZONO": dict(
        nombre="Total column ozone (OMI)",
        definicion="Total amount of ozone above the place, measured by the OMI instrument.",
        tecnica="Total column ozone retrieved by the Ozone Monitoring Instrument aboard the Aura satellite. Monthly "
                "mean of the daily observations.",
        producto="TOMS and OMI Merged Ozone Data v3, band ozone; Google Earth Engine collection TOMS/MERGED. Only "
                 "the OMI period, from 2005, is used.",
        aviso="The collection merges several instruments since 1978; only the OMI period is analysed here so that a "
              "change of instrument is not mistaken for a trend.",
        relevancia="It is the direct satellite monitoring of the ozone layer, which absorbs harmful ultraviolet "
                   "radiation."),
    "FLDAS_TEMP": dict(
        nombre="Air temperature (FLDAS)",
        definicion="How warm or cold the air near the ground is, on a finer grid than that of the reanalysis.",
        tecnica="Near-surface air temperature that drives the FLDAS model: it is that of MERRA-2 taken to a 0.1° "
                "grid. It is not a source independent of “Air temperature”; it is included because it allows whole "
                "countries and the world to be analysed.",
        producto="FLDAS Noah (forced with MERRA-2 and CHIRPS), field Tair_f_tavg; Google Earth Engine collection "
                 "NASA/FLDAS/NOAH01/C/GL/M/V001.",
        relevancia="It is the basic indicator of warming; on a fine grid it shows how it changes within a country."),
    "FLDAS_ESCURRIMIENTO": dict(
        nombre="Runoff (FLDAS)",
        definicion="Rain and meltwater that does not stay in the soil and flows towards streams, rivers and aquifers.",
        tecnica="Simulated total runoff: surface plus subsurface (baseflow). It is an estimate from a land-surface "
                "model, not a discharge measured in a river.",
        producto="FLDAS Noah (forced with MERRA-2 and CHIRPS), fields Qs_tavg + Qsb_tavg; Google Earth Engine "
                 "collection NASA/FLDAS/NOAH01/C/GL/M/V001.",
        relevancia="It determines how much water reaches rivers, reservoirs and aquifers: it is the basis of water "
                   "supply and of flood risk."),
    "MAR_SST": dict(
        nombre="Sea surface temperature",
        definicion="How warm the water is at the surface of the sea.",
        tecnica="Sea surface temperature from the OISST analysis, which combines satellites, buoys and ships by "
                "optimum interpolation. Monthly mean of the daily fields.",
        producto="NOAA OISST v2.1, band sst; Google Earth Engine collection NOAA/CDR/OISST/V2_1.",
        relevancia="The ocean absorbs most of the heat the planet gains; its temperature controls hurricanes, "
                   "corals and fisheries."),
    "MAR_SST_MODIS": dict(
        nombre="Sea surface temperature (MODIS)",
        definicion="The temperature of the water at the surface of the sea, measured by the Aqua satellite.",
        tecnica="Sea surface temperature retrieved in the infrared by MODIS Aqua, under clear skies. Monthly mean "
                "of the daily fields.",
        producto="MODIS Aqua L3 SMI, band sst; Google Earth Engine collection NASA/OCEANDATA/MODIS-Aqua/L3SMI.",
        relevancia="It is an independent satellite measurement of sea temperature, which allows the long-term "
                   "analysis to be confirmed."),
    "MAR_CLOROFILA": dict(
        nombre="Ocean chlorophyll (MODIS)",
        definicion="How much chlorophyll there is in the water: it indicates the amount of phytoplankton, the "
                   "microscopic plants on which marine life depends.",
        tecnica="Near-surface chlorophyll-a concentration, estimated from ocean colour. Monthly mean of the daily "
                "fields.",
        producto="MODIS Aqua L3 SMI, band chlor_a; Google Earth Engine collection NASA/OCEANDATA/MODIS-Aqua/L3SMI.",
        aviso="The record is analysed from 2003 to 2021. Since 2022 the Aqua satellite has been drifting in orbit "
              "and chlorophyll shows a global jump that does not come from the ocean, so those years are discarded. "
              "In addition, its distribution is very skewed: a few intense blooms weigh heavily in the mean.",
        relevancia="Phytoplankton is the base of the marine food chain and produces about half of the planet's oxygen."),
    # --- Extremes ---
    "EXT_TXX": dict(
        nombre="Hottest day of the year",
        definicion="The highest maximum temperature recorded in the year.",
        tecnica="ETCCDI index TXx: annual maximum of the daily maximum temperature at 2 m.",
        producto=_ext("T2M_MAX"), aviso=_AVISO_EXT,
        relevancia="The most intense heat of the year tests health, the power grid and crops more than the average does."),
    "EXT_TNN": dict(
        nombre="Coldest night of the year",
        definicion="The lowest minimum temperature recorded in the year.",
        tecnica="ETCCDI index TNn: annual minimum of the daily minimum temperature at 2 m.",
        producto=_ext("T2M_MIN"), aviso=_AVISO_EXT,
        relevancia="The most intense cold of the year determines damaging frosts and which species and pests "
                   "survive the winter."),
    "EXT_DIAS_CALOR": dict(
        nombre="Days of extreme heat for the place",
        definicion="How many days of the year were hotter than 90 % of the days from 1981 to 2010 at that same place.",
        tecnica="Days per year with maximum temperature above the 90th percentile of the daily maxima of the "
                "1981-2010 base period of the site. Simplified variant of the ETCCDI index TX90p: the threshold is "
                "a single one for the whole year, not one per calendar day.",
        producto=_ext("T2M_MAX"), aviso=_AVISO_EXT,
        relevancia="It measures heat waves by each place's own yardstick: what is extreme in a temperate city is "
                   "normal in the desert."),
    "EXT_DIAS_35": dict(
        nombre="Days above 35 °C",
        definicion="How many days of the year the maximum temperature exceeded 35 °C.",
        tecnica="Days per year with daily maximum temperature at 2 m above 35 °C (fixed threshold).",
        producto=_ext("T2M_MAX"), aviso=_AVISO_EXT,
        relevancia="Above 35 °C heat stroke, crop losses and energy demand for cooling increase."),
    "EXT_NOCHES_20": dict(
        nombre="Tropical nights",
        definicion="How many nights of the year the temperature did not drop below 20 °C.",
        tecnica="ETCCDI index TR: days per year with daily minimum temperature above 20 °C.",
        producto=_ext("T2M_MIN"), aviso=_AVISO_EXT,
        relevancia="Warm nights prevent the body and cities from recovering from the heat of the day."),
    "EXT_RX1": dict(
        nombre="Maximum one-day rainfall",
        definicion="How much it rained on the wettest day of the year.",
        tecnica="ETCCDI index Rx1day: annual maximum of daily precipitation.",
        producto=_ext("PRECTOTCORR"), aviso=_AVISO_EXT,
        relevancia="The most intense downpours cause flash floods and landslides; a warmer atmosphere holds more vapour."),
    "EXT_R10": dict(
        nombre="Heavy rain days",
        definicion="How many days of the year it rained 10 mm or more.",
        tecnica="ETCCDI index R10mm: days per year with daily precipitation of 10 mm or more.",
        producto=_ext("PRECTOTCORR"), aviso=_AVISO_EXT,
        relevancia="Heavy rain recharges reservoirs and aquifers, but it also erodes the soil and saturates drainage."),
    "EXT_CDD": dict(
        nombre="Longest dry spell",
        definicion="The largest number of consecutive days without rain in the year.",
        tecnica="ETCCDI index CDD: maximum number of consecutive days with precipitation below 1 mm. Here the spell "
                "is counted within each calendar year.",
        producto=_ext("PRECTOTCORR"), aviso=_AVISO_EXT,
        relevancia="Long dry spells deplete soil moisture and raise the risk of drought and wildfire."),
}

# Textos cortos que se repiten: unidades, temas, clases de dato, fuentes y resoluciones.
FRASES: dict[str, str] = {
    # unidades
    "días": "days", "días/año": "days/year", "días/mes": "days/month", "fracción (0–1)": "fraction (0–1)",
    "grados-día/mes": "degree-days/month", "mm/día": "mm/day", "unidades Dobson": "Dobson units",
    "cm de agua": "cm of water",
    # temas
    "Temperatura": "Temperature", "Hidrología": "Hydrology", "Humedad atmosférica": "Atmospheric moisture",
    "Atmósfera": "Atmosphere", "Océano": "Ocean", "Vegetación": "Vegetation", "Extremos": "Extremes",
    # clases de dato
    "Reanálisis o modelo": "Reanalysis or model", "Observación satelital": "Satellite observation",
    "Modelo de superficie terrestre": "Land-surface model", "Análisis de observaciones": "Analysis of observations",
    "Índice anual de extremos": "Annual extremes index",
    # fuentes
    "MERRA-2 (reanálisis de la NASA), vía NASA POWER": "MERRA-2 (NASA reanalysis), via NASA POWER",
    "MERRA-2 (reanálisis de la NASA), datos diarios vía NASA POWER": "MERRA-2 (NASA reanalysis), daily data via NASA POWER",
    "CERES SYN1deg (NASA), vía NASA POWER": "CERES SYN1deg (NASA), via NASA POWER",
    "GPM IMERG (satélites de la NASA y JAXA), vía Google Earth Engine": "GPM IMERG (NASA and JAXA satellites), via Google Earth Engine",
    "MODIS a bordo del satélite Terra (NASA), vía Google Earth Engine": "MODIS aboard the Terra satellite (NASA), via Google Earth Engine",
    "MODIS a bordo del satélite Aqua (NASA), vía Google Earth Engine": "MODIS aboard the Aqua satellite (NASA), via Google Earth Engine",
    "GRACE y GRACE-FO (satélites de la NASA y Alemania), vía Google Earth Engine": "GRACE and GRACE-FO (NASA and German satellites), via Google Earth Engine",
    "OMI a bordo del satélite Aura (NASA), vía Google Earth Engine": "OMI aboard the Aura satellite (NASA), via Google Earth Engine",
    "FLDAS (modelo hidrológico de la NASA), vía Google Earth Engine": "FLDAS (NASA hydrological model), via Google Earth Engine",
    "OISST (análisis de la NOAA con satélites, boyas y barcos), vía Google Earth Engine": "OISST (NOAA analysis with satellites, buoys and ships), via Google Earth Engine",
    # resoluciones
    "0.5° de latitud × 0.625° de longitud (unos 50 km)": "0.5° latitude × 0.625° longitude (about 50 km)",
    "0.1° nativo, muestreado a 0.5° (unos 50 km)": "0.1° native, sampled at 0.5° (about 50 km)",
    "0.25° nativo, muestreado a 0.5° (unos 50 km)": "0.25° native, sampled at 0.5° (about 50 km)",
    "1 km nativo, muestreado a 0.5° (unos 50 km)": "1 km native, sampled at 0.5° (about 50 km)",
    "4 km nativo, muestreado a 0.5° (unos 50 km)": "4 km native, sampled at 0.5° (about 50 km)",
    "1° × 1° (unos 100 km)": "1° × 1° (about 100 km)",
    "mascons de 3° (unos 300 km), en rejilla de 0.5°": "3° mascons (about 300 km), on a 0.5° grid",
}

# Qué tan independientes son las dos fuentes de cada pareja (ver `variables.PAREJAS`).
PAREJAS_EN: dict[str, str] = {
    "MODIS_AOD": "The CERES product assimilates MODIS observations, so the two sources are not fully independent.",
    "OMI_OZONO": "MERRA-2 assimilates satellite ozone measurements, including those of OMI: the two sources are not "
                 "fully independent.",
    "GPM_LLUVIA": "Satellite observation versus a reanalysis corrected with rain gauges: largely independent sources.",
    "MAR_SST_MODIS": "Different sensors (MODIS infrared versus AVHRR with buoys and ships): independent sources.",
    "MODIS_EVI": "Same instrument with a different formula: it checks that the result does not depend on the chosen index.",
}
