# -*- coding: utf-8 -*-
"""
R2_03_content: 改訂原稿(v5)の本文・表・参考文献の内容。数値は results/R2_results.json から埋め込む（手入力しない）。
段落の指定は v4 の段落番号（P###）に対応する。{ref:key} は引用プレースホルダ。
"""
import json
from pathlib import Path

import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as _P
R1 = _P.R1
R = json.load(open(R1 / "results" / "R2_results.json", encoding="utf-8"))
D = R["desc"]; PR = R["primary"]; SP = R["spatial"]; B4 = SP["block_k4"]; SENS = R["sens"]; CK = R["cook"]
MINUS = "\u2212"
R3 = json.load(open(R1 / "results" / "R3_results.json", encoding="utf-8"))
RT = json.load(open(R1 / "results" / "R7_t_results.json", encoding="utf-8"))   # t分布による推論（小標本感度）
R7 = json.load(open(R1 / "results" / "R7_results.json", encoding="utf-8"))   # SLM の直接・間接・総効果
E4 = R7["k4"]; EK = R7["k_sens"]
def eff_txt(e, nd=1): return f"{f(e['est'], nd)} (95% interval {f(e['lo'], nd)} to {f(e['hi'], nd)})"


def f(x, nd=1, sign=False):
    s = f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"
    return s.replace("-", MINUS)


def pv(p, eq=True):
    if p < 0.001: return "<i>p</i> < 0.001"
    return f"<i>p</i> = {p:.3f}" if eq else f"{p:.3f}"


def pnum(p): return "<0.001" if p < 0.001 else f"{p:.3f}"
def stars(p): return "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))


c1 = PR["coef"][1]; pm = PR["per_month"]; psd = PR["per_sd"]
slm_pm = B4["slm_beta"] / 12; sem_pm = B4["sem_beta"] / 12
def zci(beta12, z):
    se = abs(beta12 / z); return beta12 - 1.96 * se, beta12 + 1.96 * se
slm_lo, slm_hi = zci(slm_pm, B4["slm_z"]); sem_lo, sem_hi = zci(sem_pm, B4["sem_z"])
ks = {int(k): v for k, v in R["spatial_k"].items()}
slm_p_rng = (min(v["sb"]["slm_p"] for v in ks.values()), max(v["sb"]["slm_p"] for v in ks.values()))
sem_p_rng = (min(v["sb"]["sem_p"] for v in ks.values()), max(v["sb"]["sem_p"] for v in ks.values()))
sel_names = {"SLM": "spatial lag", "SEM": "spatial error", "OLS": "ordinary least squares"}
SEL = sel_names[SP["selected"]]
IND = SENS["indicators"]; EXC = SENS["exclusions"]; GRID = SENS["grid"]; CAT = SENS["categories"]; ADD = SENS["added"]; ORIG = SENS["original_spec"]
corr_cols = R["corr"]["cols"]; CR = R["corr"]["r"]; CP = R["corr"]["p"]
def corr(a, b): i, j = corr_cols.index(a), corr_cols.index(b); return CR[i][j], CP[i][j]
cook_over = CK["over"]
def lst(xs, conj="and"):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else (", ".join(xs[:-1]) + (f", {conj} " if len(xs) > 2 else f" {conj} ") + xs[-1])

n_over = len(cook_over)
y_mean, y_sd = D["y"]["mean"], D["y"]["sd"]
x_mean, x_sd = D["x"]["mean"], D["x"]["sd"]

# ------------------------------------------------------------------ 参考文献（初出順に自動採番。誌の様式: 著者3名まで+et al.）
REFS = {
 "who": "World Health Organization. Cardiovascular diseases (CVDs) [Internet]. Geneva: World Health Organization; 2025 [cited 2026 Nov 2]. Available from: https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds)",
 "vital": "Ministry of Health, Labour and Welfare (JP). Vital statistics of Japan, annual total of the monthly report 2022 (approximate figures): Table 10, deaths and death rates (per 100,000 population) of the leading causes of death (up to rank 10) by prefecture [Internet]. Tokyo: Ministry of Health, Labour and Welfare; 2023 [cited 2026 Nov 2]. Available from: https://www.mhlw.go.jp/toukei/saikin/hw/jinkou/geppo/nengai22/index.html",
 "stewart": "Stewart S, Keates AK, Redfern A, et al. Seasonal variations in cardiovascular disease. Nat Rev Cardiol. 2017;14(11):654-664.",
 "bhaskaran": "Bhaskaran K, Hajat S, Haines A, et al. Effects of ambient temperature on the incidence of myocardial infarction. Heart. 2009;95(21):1760-1769.",
 "ye": "Ye X, Wolff R, Yu W, et al. Ambient temperature and morbidity: a review of epidemiological evidence. Environ Health Perspect. 2012;120(1):19-28.",
 "keatinge": "Keatinge WR, Coleshaw SR, Cotter F, et al. Increases in platelet and red cell counts, blood viscosity, and arterial pressure during mild surface cooling: factors in mortality from coronary and cerebral thrombosis in winter. Br Med J (Clin Res Ed). 1984;289(6456):1405-1408. doi:10.1136/bmj.289.6456.1405",
 "cheng": "Cheng X, Su H. Effects of climatic temperature stress on cardiovascular diseases. Eur J Intern Med. 2010;21(3):164-167.",
 "gasparrini": "Gasparrini A, Guo Y, Hashizume M, et al. Mortality risk attributable to high and low ambient temperature: a multicountry observational study. Lancet. 2015;386(9991):369-375.",
 "zhao": "Zhao Q, Guo Y, Ye T, et al. Global, regional, and national burden of mortality associated with non-optimal ambient temperatures from 2000 to 2019: a three-stage modelling study. Lancet Planet Health. 2021;5(7):e415-e425. doi:10.1016/S2542-5196(21)00081-4",
 "jma_obs": "Japan Meteorological Agency. Download of past weather data (monthly values) [Internet]. Tokyo: Japan Meteorological Agency [cited 2026 Mar 2]. Available from: https://www.data.jma.go.jp/risk/obsdl/index.php",
 "anselin1995": "Anselin L. Local indicators of spatial association—LISA. Geogr Anal. 1995;27(2):93-115.",
 "anselin1988": "Anselin L. Spatial Econometrics: Methods and Models. Dordrecht: Kluwer Academic; 1988.",
 "mercer": "Mercer JB. Cold—an underrated risk factor for health. Environ Res. 2003;92(1):8-13.",
 "kario": "Kario K. Cold-induced hypertension as life-environment disease in winter: focus on data from Japan. Hypertension. 2026. doi:10.1161/HYPERTENSIONAHA.125.26518",
 "narita": "Narita K, Hoshide S, Kario K. Seasonal variation in day-by-day home blood pressure variability and effect on cardiovascular disease incidence. Hypertension. 2022;79(9):2062-2070.",
 "hanazawa": "Hanazawa T, Asayama K, Watabe D, et al. Association between amplitude of seasonal variation in self-measured home blood pressure and cardiovascular outcomes: HOMED-BP study. J Am Heart Assoc. 2018;7(10):e008509.",
 "umishio2019": "Umishio W, Ikaga T, Kario K, et al. Cross-sectional analysis of the relationship between home blood pressure and indoor temperature in winter: a nationwide Smart Wellness Housing Survey in Japan. Hypertension. 2019;74(4):756-766.",
 "saeki2017": "Saeki K, Obayashi K, Kurumatani N. Platelet count and indoor cold exposure among elderly people: a cross-sectional analysis of the HEIJO-KYO study. J Epidemiol. 2017;27(12):562-567.",
 "tabara": "Tabara Y, Kushida O, Ozaki E, et al. Effects of room temperature on home morning, evening, and sleep blood pressure: the Shizuoka study. J Hypertens. 2026;44(1):109-115. doi:10.1097/HJH.0000000000004154",
 "umishio2025": "Umishio W, Kiuchi S, Ojima T, et al. Combination of housing type (detached houses vs flats) and tenure (owned vs rented) in relation to cardiovascular mortality: findings from a 6-year cohort study in Japan. BMJ Public Health. 2025;3(2):e003073. doi:10.1136/bmjph-2025-003073",
 "gbd": "GBD 2021 Japan Collaborators. Three decades of population health changes in Japan, 1990-2021: a subnational analysis for the Global Burden of Disease Study 2021. Lancet Public Health. 2025;10(4):e321-e332. doi:10.1016/S2468-2667(25)00044-1",
 "ogata": "Ogata S, Kiyoshige E, Yoshikawa Y, et al. Quantifying the contributions of cardiovascular risk factors to cardiovascular disease trends in 21st century Japan: a microsimulation study. Lancet Reg Health West Pac. 2025;60:101623. doi:10.1016/j.lanwpc.2025.101623",
 "iwabe": "Iwabe Y, Satoh M, Nobayashi H, et al. Regional disparities in blood pressure control after hypertension treatment initiation in Japan: a real-world data analysis. Hypertens Res. 2026;49(2):328-339. doi:10.1038/s41440-025-02454-y",
 "roelfs": "Roelfs DJ, Shor E, Davidson KW, et al. Losing life and livelihood: a systematic review and meta-analysis of unemployment and all-cause mortality. Soc Sci Med. 2011;72(6):840-854.",
 "dupre": "Dupre ME, George LK, Liu G, et al. The cumulative effect of unemployment on risks for acute myocardial infarction. Arch Intern Med. 2012;172(22):1731-1737.",
 "miyazaki": "Miyazaki J, Shirai K, Kimura T, et al. Purpose in life (Ikigai) and employment status in relation to cardiovascular mortality: the Japan Collaborative Cohort Study. BMJ Open. 2022;12(10):e059725. doi:10.1136/bmjopen-2021-059725",
 "okui2020": "Okui T. Socioeconomic disparities in all-cause and cause-specific mortality rates among municipalities in Japan, 1999–2019. Int J Environ Res Public Health. 2020;17(24):9213.",
 "okui2022": "Okui T, Park J. Difference in the prevalence of hypertension and its risk factors depending on area-level deprivation in Japan. BMC Res Notes. 2022;15(1):37.",
 "umishio2024": "Umishio W, Ikaga T, Kario K, et al. Effect of living in well-insulated warm houses on hypertension and cardiovascular diseases based on a nationwide epidemiological survey in Japan: a modelling and cost-effectiveness analysis. BMJ Public Health. 2024;2(2):e001143.",
 "ohashi": "Ohashi Y, Ihara T, Oka K, et al. Machine learning analysis and risk prediction of weather-sensitive mortality related to cardiovascular disease during summer in Tokyo, Japan. Sci Rep. 2023;13(1):17020. doi:10.1038/s41598-023-44181-9",
 "yuan": "Yuan L, Madaniyazi L, Vicedo-Cabrera AM, et al. Non-optimal temperature-attributable mortality and morbidity burden by cause, age and sex under climate and population change scenarios: a nationwide modelling study in Japan. Lancet Reg Health West Pac. 2024;52:101214.",
 "rothman": "Rothman KJ, Greenland S, Lash TL. Modern Epidemiology. 3rd ed. Philadelphia: Lippincott Williams & Wilkins; 2008.",
 "mihara": "Mihara H, Murayama A, Nanjo S, et al. Factors correlated with drug use for constipation: perspectives from the 2016 open Japanese National Database. BMC Gastroenterol. 2020;20(1):284. doi:10.1186/s12876-020-01425-6",
 "england": "Tolladay J, Yau C. Investigating the effect of climate and air pollution on prescription uptake in England. BMC Public Health. 2026;26(1). doi:10.1186/s12889-026-28114-5",
 "spain": "Royé D, Tobías A, Figueiras A, et al. Temperature-related effects on respiratory medical prescriptions in Spain. Environ Res. 2021;202:111695. doi:10.1016/j.envres.2021.111695",
 "ndbguide": "Ministry of Health, Labour and Welfare (JP). The 10th NDB Open Data: explanatory guide and prescription-drug tables [Internet]. Tokyo: Ministry of Health, Labour and Welfare; 2025 [cited 2026 Nov 2]. Available from: https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00016.html",
 "lesage": "LeSage J, Pace RK. Introduction to Spatial Econometrics. Boca Raton: Chapman and Hall/CRC; 2009. doi:10.1201/9781420064254",
 "ddd": "World Health Organization. Defined daily dose (DDD): ATC/DDD toolkit [Internet]. Geneva: World Health Organization [cited 2026 Nov 2]. Available from: https://www.who.int/tools/atc-ddd-toolkit/about-ddd",
 "popn": "Statistics Bureau of Japan. Population estimates as of October 1, 2023: Tables 2 and 3, and reference table of population by prefecture, age group (5-year), and sex [Internet]. Tokyo: Statistics Bureau of Japan [cited 2026 Nov 2]. Available from: https://www.stat.go.jp/data/jinsui/2023np/index.html",
 "physn": "Ministry of Health, Labour and Welfare (JP). Statistics of physicians, dentists and pharmacists 2022: Statistical Table 10 [Internet]. Tokyo: Ministry of Health, Labour and Welfare [cited 2026 Nov 2]. Available from: https://www.mhlw.go.jp/toukei/saikin/hw/ishi/22/index.html",
 "lfs": "Statistics Bureau of Japan. Labour Force Survey: annual results by prefecture, time-series Table 6 (model-based unemployment rates) [Internet]. Tokyo: Statistics Bureau of Japan [cited 2026 Nov 2]. Available from: https://www.stat.go.jp/data/roudou/pref/index.htm",
 "income": "Economic and Social Research Institute, Cabinet Office (JP). Annual report on prefectural accounts, FY2022: Summary Table 7, per capita prefectural income [Internet]. Tokyo: Cabinet Office [cited 2026 Nov 2]. Available from: https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/tables/2022/soukatu7.xlsx",
 "nhns": "Ministry of Health, Labour and Welfare (JP). National Health and Nutrition Survey 2016: Table 55, age-adjusted salt intake by sex and prefecture [Internet]. Tokyo: Ministry of Health, Labour and Welfare [cited 2026 Nov 2]. Available from: https://www.mhlw.go.jp/content/001693631.pdf",
}
# v4 の引用番号 → キー（自動変換用）
OLD2KEY = {1: "who", 2: "vital", 3: "stewart", 4: "bhaskaran", 5: "ye", 6: "keatinge", 7: "cheng", 8: "gasparrini", 9: "zhao", 10: "jma_obs",
           11: "anselin1995", 12: "anselin1988", 13: "mercer", 14: "kario", 15: "narita", 16: "hanazawa", 17: "umishio2019", 18: "saeki2017",
           19: "tabara", 20: "umishio2025", 21: "gbd", 22: "ogata", 23: "iwabe", 24: "roelfs", 25: "dupre", 26: "miyazaki", 27: "okui2020",
           28: "okui2022", 29: "umishio2024", 30: "ohashi", 31: "yuan", 32: "rothman"}

# ------------------------------------------------------------------ 本文
TITLE = "Cold-Season Duration and Cardiovascular Drug Dispensing Across Japanese Prefectures: A Nationwide Ecological Study"
RUNNING = "Cold season and CVD drug dispensing in Japan"
KEYWORDS = "cardiovascular disease; cold exposure; ecological study; Japan; NDB Open Data; spatial analysis"

ABS_OBJ = ("To examine whether the length of the cold season is associated with the quantity of cardiovascular drugs dispensed across Japanese prefectures, "
           "and whether any association is robust to spatial dependence.")
ABS_METH = (f"In this nationwide ecological study of all 47 prefectures, the outcome was the number of tablets of five cardiovascular drug categories dispensed per resident "
            f"through outpatient prescriptions in fiscal year 2023 (10th National Database [NDB] Open Data). The exposure was the proportion of 60 months (2016–2020) with a mean temperature below 5°C "
            f"at one Japan Meteorological Agency station per prefecture. We fitted ordinary least squares (OLS) regression adjusted for aging, physician density, unemployment, and income, "
            f"then spatial lag and spatial error models.")
ABS_RES = (f"Prefectures dispensed {f(y_mean)} tablets per resident per year on average (SD {f(y_sd)}). In OLS, each additional cold month per year was associated with {f(pm['beta'])} more tablets per resident per year "
           f"(95% CI {f(pm['ci_lo'])} to {f(pm['ci_hi'])}; {pv(PR['p_hc3'])}), alongside aging rate. Residuals were spatially autocorrelated (Moran's I = {f(B4['moran_res'][0],2)}; {pv(B4['moran_res'][2])}). "
           f"LM diagnostics did not clearly distinguish lag from error dependence; the spatial lag coefficient was {f(slm_pm)} tablets ({pv(B4['slm_p'])}; total effect {f(E4['total']['est'])}, 95% interval {f(E4['total']['lo'])} to {f(E4['total']['hi'])}) and the spatial error coefficient {f(sem_pm)} ({pv(B4['sem_p'])}). "
           f"The association was attenuated after adjustment for smoking.")
ABS_CON = ("A longer cold season was associated with larger dispensed quantities in conventional regression, but not robustly across spatial specifications. "
           "These exploratory ecological findings do not establish causation.")

HIGHLIGHTS = [
    "• Prefectures with longer cold seasons dispensed more cardiovascular tablets per resident in conventional regression.",
    f"• Each additional cold month per year corresponded to about {f(pm['beta'],0)} tablets per resident per year ({f(PR['pct_of_mean_per_month'])}% of the mean).",
    "• Residuals were spatially clustered; the association was significant in OLS and the spatial error model but not in the spatial lag model.",
    "• These ecological findings are exploratory and do not establish causation.",
]

INTRO_P22 = ("Cardiovascular diseases (CVDs), including ischemic heart disease and cerebrovascular disease, remain a leading source of mortality and healthcare use worldwide.{ref:who} "
             "In Japan, heart disease is the second leading cause of death after malignant neoplasms, and cardiovascular diseases continue to require substantial long-term pharmacological management.{ref:vital} "
             "Whether regional climate conditions are reflected in routine pharmaceutical use is relevant for health-system planning.")
INTRO_P24 = ("Most temperature-CVD research has focused on acute clinical outcomes such as emergency visits, hospitalizations, or deaths. By contrast, dispensing data capture a different health-system signal: "
             "the geographic distribution of pharmacological management for chronic cardiovascular conditions. Prefecture-level dispensed quantities should not be interpreted as individual disease incidence or prevalence, "
             "but they can indicate regional differences in treatment demand and continuing healthcare utilization.")
INTRO_NEW = ("Temperature has been examined in relation to medication use in other settings. In Japan, an ecological study using the 2016 NDB Open Data evaluated factors correlated with constipation drug use, including low outside temperature.{ref:mihara} "
             "Studies from England and Spain have examined climate and prescribing.{ref:england,spain} We are not aware of a prefecture-level analysis of cold-season duration and cardiovascular drug quantities in Japan. "
             "The present study focuses on cardiovascular drug categories, summarizes cold exposure as the proportion of cold months, and explicitly evaluates spatial dependence.")
INTRO_P25 = ("Japan's archipelago spans approximately 25 degrees of latitude, from subarctic Hokkaido to subtropical Okinawa, and the proportion of cold months (mean monthly temperature <5°C) varies substantially across prefectures.{ref:jma_obs} "
             "This geographic gradient, combined with the availability of the National Database (NDB) Open Data covering nearly all insurance claims in Japan, provides an opportunity to examine whether the length of the cold season aligns with cardiovascular drug dispensing at a nationwide ecological scale.")
INTRO_P27 = ("In this study, we examined the association between the proportion of cold months and the quantity of cardiovascular drugs dispensed per resident across Japanese prefectures, adjusted for selected demographic and socioeconomic covariates, "
             "and evaluated whether the association was robust to spatial dependence.")

M_P31 = ("We conducted a nationwide ecological study in which the Japanese prefecture (N = 47) served as the unit of analysis. Prefecture-level aggregate data were used because individual-level geographic information is not available from NDB Open Data. "
         "The outcome period was fiscal year 2023 (April 2023 through March 2024). Climate exposure was measured over the 60 months from January 2016 to December 2020 and was not matched to the outcome year.")
M_OUT1 = ("The outcome was derived from the 10th NDB Open Data (released 2025; fiscal year 2023; tables that exclude claims paid with public expenditure), using the table of oral drugs prescribed in outpatient settings and dispensed outside the medical institution (“outpatient, external”), "
          "tabulated by prefecture and therapeutic category.{ref:ndbguide} Five therapeutic categories were included: 214 (antihypertensives), 217 (vasodilators), 218 (antihyperlipidemics), 219 (other cardiovascular agents), and 333 (anticoagulants). "
          "The table reports the quantity of each drug product in its own dosing unit. To avoid summing quantities measured in different units, the primary outcome included only rows with the unit “tablet” (1,178 of 1,239 product rows, 93.7% of total quantity), "
          "and the primary outcome was the number of tablets dispensed per resident per year. This outcome is a dispensed quantity, not the number of prescriptions, patients, or defined daily doses (DDD).{ref:ddd}")
M_OUT2 = ("Quantities were divided by the total resident population on 1 October 2023.{ref:popn} Prefecture attribution reflects the location of the dispensing pharmacy or medical institution, not the patient’s residence. "
          "The tables list a limited number of products per category so drugs outside the published lists are not captured, "
          "and cells with small counts are masked: 1,615 of 55,366 prefecture-by-product cells in tablet rows (2.9%) were not numeric and were not imputed. The outcome is therefore a lower bound of the tablets dispensed.")
M_OUT3 = ("Because the published tables do not provide quantities cross-classified by prefecture, age, and sex, direct age- and sex-standardization was not possible. The primary analysis therefore used crude quantities per resident and adjusted for the aging rate. As a sensitivity analysis, we calculated an indirectly age- and sex-standardized outcome: the expected number of tablets in each prefecture was obtained by applying national tablet quantities per resident by sex and 5-year age group (same drug categories and unit; ages ≥85 years combined) to the population of the prefecture by sex and age group on 1 October 2023,{ref:popn} and the observed-to-expected ratio was multiplied by the national mean quantity per resident. "
          "We also analysed the sum of all units of measurement (the definition used in the initial analysis), category 214 alone, and each category separately.")
M_P37 = ("Five temperature indicators were computed from Japan Meteorological Agency (JMA) monthly mean temperatures of one station per prefecture for 60 months (January 2016–December 2020):{ref:jma_obs} "
         "(1) mean annual temperature, (2) annual temperature range (highest minus lowest of the 12 calendar-month means), (3) winter mean temperature (December–February), (4) temperature variability (standard deviation of the 60 monthly means), "
         "and (5) the cold month ratio, defined as the number of months with a mean temperature below 5°C divided by 60. Because the ratio is based on 60 months, it takes multiples of 1/60; "
         "a ratio increase of 1/12 corresponds to one additional cold month per year on average.")
M_EXP2 = ("The JMA station was located in the prefectural capital in 44 prefectures and in Kumagaya (Saitama), Hikone (Shiga), and Shimonoseki (Yamaguchi) for the three remaining prefectures. "
          "A single station cannot represent the exposure of all residents of a prefecture, and no population weighting was applied. The study was not preregistered. "
          "The 2016–2020 period was used to characterize the regional cold-season pattern and precedes the outcome year. Stations and exposures are given in Supplementary Table S1.")
M_EXP3 = ("The cold month ratio is designated as the primary exposure because it captures the cumulative duration of the cold season. Because it also showed the best model fit in the initial analysis of these data, this designation is not independent of the data. "
          "The other four indicators are analysed as sensitivity analyses, including their multivariable models, and all findings are regarded as exploratory.")
M_P39 = "Four covariates were included as potential confounders and were matched as closely as possible to the outcome year (fiscal year 2023):"
M_COV = [
    ("Physicians per 100,000 population", ": physicians working in medical facilities, 31 December 2022 (Survey of Physicians, Dentists and Pharmacists).{ref:physn}"),
    ("Unemployment rate (%)", ": annual model-based prefectural unemployment rate, calendar year 2023 (Labour Force Survey).{ref:lfs}"),
    ("Aging rate (%)", ": population aged ≥65 years as a percentage of the total population on 1 October 2023 (Population Estimates).{ref:popn}"),
    ("Per capita prefectural income (10,000 yen)", ": fiscal year 2022 (Annual Report on Prefectural Accounts).{ref:income}"),
]
M_COV_NEW = ("As sensitivity analyses, body mass index, smoking prevalence, and systolic blood pressure (age- and sex-standardized means or prevalence among specific health checkup attendees aged 40–74 years, fiscal year 2022; NDB Open Data) "
             "and age-adjusted sodium intake (National Health and Nutrition Survey 2016; unavailable for one prefecture) were added to the model.{ref:nhns} Because systolic blood pressure may lie on the pathway between cold exposure and drug use, it was examined separately; the share of attendees with systolic blood pressure ≥140 mmHg was used as a proxy for hypertension prevalence. Missing covariate data were not imputed.")
M_P47H = "Primary Exposure and Model Specification"
M_P48 = ("The primary model regressed dispensed tablets per resident per year on the cold month ratio and the four covariates. The other four temperature indicators were each entered in separate multivariable models with the same covariates "
         "(Benjamini–Hochberg adjustment across the five indicators).")
M_P50 = ("The primary model was fitted by ordinary least squares (OLS) with heteroscedasticity-consistent (HC3) standard errors; 95% confidence intervals and p values were based on the normal approximation, and t-distribution reference values (41 residual degrees of freedom) were examined for the primary exposure as a small-sample check. "
         "The coefficient of the cold month ratio is expressed per additional cold month per year (the ratio coefficient divided by 12) and per standard deviation of the ratio. "
         "Variance inflation factors (VIF) were computed to assess multicollinearity. Residual diagnostics included the Shapiro-Wilk test (normality), the Breusch-Pagan test (heteroscedasticity), and Cook’s distance (influential prefectures; threshold 4/n).")
M_P51H = "Spatial Analysis"
M_P52 = ("Spatial autocorrelation was assessed for the outcome, the cold month ratio, and the OLS residuals using Global Moran’s I with a K-nearest neighbors (KNN, k = 4) spatial weights matrix based on great-circle distances between prefecture centroids "
         "(symmetrized, row-standardized; 999 permutations; random seed 20261102). KNN was used because Queen contiguity left Hokkaido and Okinawa as spatial islands. Local Moran’s I (LISA) identified local clusters of the outcome at p < 0.05, without multiplicity correction across the 47 prefectures; the LISA results are descriptive and exploratory.{ref:anselin1995} "
         "Lagrange multiplier (LM) tests for spatial lag and spatial error dependence and their robust versions were computed on the OLS residuals. Spatial lag and spatial error models were fitted by maximum likelihood.{ref:anselin1988} "
         "In the spatial lag model the regression coefficient excludes feedback through neighboring prefectures; we therefore also report the average direct, indirect, and total effects of the cold month ratio,{ref:lesage} with 95% intervals from 10,000 simulations of the estimated coefficient and spatial lag parameter (random seed 20261102). "
         "By the usual decision rule for LM diagnostics, the spatial lag model is chosen when only the lag test is significant, or when both are significant and the robust lag test has the smaller p value (the error model in the converse situations; OLS if neither is significant). When neither robust test is significant, the choice is uncertain, so both models are reported side by side. "
         "This rule was specified after the initial analysis had been seen. Results are reported for k = 3–6.")
M_SENS_H = "Sensitivity Analyses"
M_SENS = ("Sensitivity analyses comprised: (1) exclusion of prefectures with Cook’s distance >4/n, of the most influential prefecture, and of Hokkaido and Okinawa, and leave-one-prefecture-out analyses; "
          "(2) alternative specifications combining the outcome (tablets or all units; five categories or category 214 only), the exposure (<5°C in 2016–2020, <5°C in fiscal year 2023, or <10°C in fiscal year 2023), and the covariate set (year-aligned or those of the initial analysis); "
          "(3) separate analyses of each drug category; (4) addition of the further covariates; (5) the indirectly age- and sex-standardized outcome. Supplementary Tables S2–S5 give the results. No multiplicity correction was applied except across the five indicators and five categories.")
M_AI_H = "Use of Generative AI"
M_AI = ("Generative AI tools were used in this work beyond improving readability and language. For the initial submission, Cursor 3.0 (Anysphere) and Google Antigravity (Google), "
        "with Claude Sonnet 4.6 and Claude Opus 4.8 (Anthropic) and Gemini 3 Pro (Google), were used to draft text and to write Python analysis scripts. For this revision, Claude Code with Claude Sonnet 5.5 (Anthropic) was used to re-examine the original analysis scripts and data, "
        "to write and run the analysis and figure code, to draft the revised text, tables, supplementary material, and response to reviewers, and to prepare the reference list. Codex (OpenAI; GPT-6.1 Sol) was used to compile official public data sources, "
        "to perform an independent reconstruction analysis, and to draft documents; its output served as a cross-check, and the year-aligned and additional covariates (body mass index, smoking, systolic blood pressure, and sodium intake) it compiled were re-extracted from the official tables by separate code written for the revision, and the values agreed. "
        "Figures were drawn by running plotting code (Matplotlib and GeoPandas), written with the assistance of Claude Code, on the numerical results. No generative AI image model was used; no image was created, altered, or retouched by an AI tool, and the figures were not edited after the code produced them. "
        "The authors are responsible for the study design, the choice of statistical methods, the interpretation of the findings, the conclusions, and the final reference list, and take full responsibility for the content. "
        "The authors reviewed and edited the AI-assisted code, numerical results, and text. The authors confirm that the text, code, and figures produced with AI assistance contain no plagiarism, and that no AI-generated material is cited as a primary source. AI systems are not authors.")

# ------------------------------------------------------------------ 結果
def sig_word(p): return "significant" if p < 0.05 else "not significant"
r_cold, p_cold = corr("y", "x")
def corr_phrase(a, label):
    r, p = corr("y", a)
    return f"{label} (r = {f(r,3)}, {pv(p)})"
pos = [(a, l) for a, l in [("x", "the cold month ratio"), ("aging_pct_2023", "the aging rate"), ("unemployment_pct_2023", "the unemployment rate"), ("physicians_per100k_2022", "physicians per 100,000"), ("income_10000yen_FY2022", "per capita income"), ("orig_Mean_Temp_avg", "mean annual temperature")] if corr("y", a)[1] < 0.05]
neg = [x for x in pos if corr("y", x[0])[0] < 0]; pos = [x for x in pos if corr("y", x[0])[0] > 0]
nonsig = [l for a, l in [("physicians_per100k_2022", "physicians per 100,000"), ("unemployment_pct_2023", "the unemployment rate"), ("income_10000yen_FY2022", "per capita income"), ("aging_pct_2023", "the aging rate"), ("x", "the cold month ratio"), ("orig_Mean_Temp_avg", "mean annual temperature")] if corr("y", a)[1] >= 0.05]
rxt, pxt = corr("x", "orig_Mean_Temp_avg")
R_P62 = (f"Across the 47 Japanese prefectures, the mean number of dispensed cardiovascular tablets was {f(y_mean)} ± {f(y_sd)} per resident per year (Table 1). The mean cold month ratio was {f(x_mean,2)} ± {f(x_sd,2)} (range: {f(D['x']['min'],2)}–{f(D['x']['max'],2)}), "
         f"corresponding to {f(D['cold_months_per_year']['mean'])} cold months per year on average. "
         f"The mean aging rate was {f(D['aging_pct_2023']['mean'])} ± {f(D['aging_pct_2023']['sd'])}%. Other covariates are given in Table 1; no covariate data were missing. "
         f"The cold month ratio is shown by prefecture in Supplementary Table S1 and Figure 1.")
R_P65 = ("Correlation analysis showed associations among climatic and socioeconomic variables (Table 2). Dispensed tablets per resident were "
         + ("positively correlated with " + lst([corr_phrase(a, l) for a, l in pos]) if pos else "not positively correlated with any variable")
         + (", and negatively correlated with " + lst([corr_phrase(a, l) for a, l in neg]) if neg else "")
         + ". "
         + f"The cold month ratio and mean annual temperature were highly intercorrelated (r = {f(rxt,3)}, {pv(pxt)}).")
NUMW = {0: "none", 1: "one", 2: "two", 3: "three", 4: "four", 5: "all"}
uni = R["uni"]
uni_sig = sorted([u for u in uni if u["p"] < 0.05], key=lambda u: -u["r2"]); uni_ns = [u for u in uni if u["p"] >= 0.05]
def ulab(u): return {"x": "the cold month ratio", "orig_Mean_Temp_avg": "mean annual temperature", "orig_Winter_temp_avg": "winter mean temperature", "orig_Temp_std": "temperature variability", "orig_Temp_range_annual": "annual temperature range"}[u["col"]]
R_P67 = (f"In univariable models, {NUMW[len(uni_sig)]} of the five temperature indicators were significantly associated with dispensed tablets per resident: "
         + "; ".join(f"{ulab(u)} (β = {f(u['beta'],1,True)} tablets per resident per year per unit; R² = {f(u['r2'],3)}; {pv(u['p'])})" for u in uni_sig)
         + (f". The remaining {'indicators were' if len(uni_ns) != 1 else 'indicator was'} not significant (R² ≤ {f(max(u['r2'] for u in uni_ns),3)})" if uni_ns else "") + " (Table 3).")
co = {c["term"]: c for c in PR["coef"]}
def cphrase(t, unit):
    c = co[t]; return f"(β = {f(c['beta'],2,True)} tablets per resident per year per {unit}; 95% CI {f(c['ci_lo'],2)} to {f(c['ci_hi'],2)}; {pv(c['p_hc3'])})"
aging_c = co["Aging rate (%)"]; unemp_c = co["Unemployment rate (%)"]; phys_c = co["Physicians per 100,000"]; inc_c = co["Per capita income (10,000 yen)"]
R_P69 = (f"In the primary multivariable OLS model (R² = {f(PR['r2'],3)}, adjusted R² = {f(PR['adj_r2'],3)}) (Table 4), the cold month ratio and the aging rate were statistically significant:")
R_P70 = (f"Cold month ratio {cphrase('Cold month ratio','1.0 unit of the ratio')}: each additional cold month per year was associated with {f(pm['beta'])} more tablets per resident per year "
         f"(95% CI {f(pm['ci_lo'])} to {f(pm['ci_hi'])}), or {f(PR['pct_of_mean_per_month'])}% of the mean, and one standard deviation of the ratio ({f(psd['sd_x'],3)}) with {f(psd['beta'])} tablets (95% CI {f(psd['ci_lo'])} to {f(psd['ci_hi'])}).")
R_P71 = f"Aging rate (β = {f(aging_c['beta'],2,True)}; {pv(aging_c['p_hc3'])}): each 1-percentage-point higher aging rate was associated with {f(aging_c['beta'],1)} more tablets per resident per year."
R_P73 = (f"Unemployment rate (β = {f(unemp_c['beta'],1,True)}; {pv(unemp_c['p_hc3'])}), physicians per 100,000 (β = {f(phys_c['beta'],2,True)}; {pv(phys_c['p_hc3'])}), and per capita income (β = {f(inc_c['beta'],3,True)}; {pv(inc_c['p_hc3'])}) were not significant. "
         f"The maximum VIF was {f(max(PR['vif'].values()))}, indicating no problematic multicollinearity.")
R_P74 = (f"Residual diagnostics did not indicate departures from normality (Shapiro-Wilk W = {f(PR['sw_W'],3)}, {pv(PR['sw_p'])}) or heteroscedasticity (Breusch-Pagan {pv(PR['bp_p'])}). "
         f"Cook’s distance exceeded 4/n in {n_over} {'prefecture' if n_over == 1 else 'prefectures'} ({lst(cook_over)}); the highest was {CK['max_name']} ({f(CK['max_val'],2)}) (Figure 2). "
         f"With t-distribution reference values for the HC3 standard errors (41 residual degrees of freedom), the cold month ratio gave {pv(RT['t']['p'])} and a 95% CI of {f(RT['t']['ci_lo'])} to {f(RT['t']['ci_hi'])} tablets per additional cold month per year.")
R_P76 = (f"Dispensed tablets per resident were strongly spatially clustered (Global Moran’s I = {f(SP['moran_y']['I'],3)}, z = {f(SP['moran_y']['z'],2)}, {pv(max(SP['moran_y']['p'],0.001))}), as was the cold month ratio (I = {f(SP['moran_x']['I'],3)}), "
         f"and the OLS residuals remained spatially autocorrelated (Moran’s I = {f(B4['moran_res'][0],3)}, {pv(B4['moran_res'][2])}) (Table 5; Figure 3). "
         f"LISA (exploratory, without multiplicity correction) identified High-High clusters in {lst([n for n, c in SP['lisa'] if c == 'High-High'])} and Low-Low clusters in {lst([n for n, c in SP['lisa'] if c == 'Low-Low'])}. "
         f"The LM tests were significant for both the lag ({pv(B4['lm_lag'][1])}) and error ({pv(B4['lm_err'][1])}) alternatives; the robust tests gave {pv(B4['rlm_lag'][1])} and {pv(B4['rlm_err'][1])}, respectively. Because neither robust test was significant at the 5% level, the diagnostics did not clearly distinguish the two specifications (the rule preferred the {SEL} model by its smaller robust p value), and both models are reported. "
         f"In the spatial lag model, the regression coefficient for each additional cold month per year was {f(slm_pm)} tablets per resident per year (95% CI {f(slm_lo)} to {f(slm_hi)}; {pv(B4['slm_p'])}; spatial lag parameter ρ = {f(B4['slm_rho'],2)}); the average direct, indirect, and total effects were {eff_txt(E4['direct'])}, {eff_txt(E4['indirect'])}, and {eff_txt(E4['total'])} tablets, respectively. "
         f"In the spatial error model, the estimate was {f(sem_pm)} tablets (95% CI {f(sem_lo)} to {f(sem_hi)}; {pv(B4['sem_p'])}; λ = {f(B4['sem_lam'],2)}). "
         f"With k = 3 to 6 neighbors, the p value of the cold month ratio ranged from {pnum(slm_p_rng[0])} to {pnum(slm_p_rng[1])} in the spatial lag model and from {pnum(sem_p_rng[0])} to {pnum(sem_p_rng[1])} in the spatial error model, and the rule preferred the {SEL} model for each k; the total effect of the spatial lag model ranged from {f(min(v['total']['est'] for v in [E4, *EK.values()]))} to {f(max(v['total']['est'] for v in [E4, *EK.values()]))} tablets, and its interval included zero in every case"
         f"{'' if all(v['sel'] == 'SLM' for v in ks.values()) else ' (except where noted in Supplementary Table S3)'}.")
R_OTH_H = "Other Analyses"
ind_by = {i["indicator"]: i for i in IND}
ind_other = [i for i in IND if not i["indicator"].startswith("Cold")]
exc_cook, exc_top, exc_hok, exc_tokyo = EXC[1], EXC[2], EXC[3], EXC[4]
slm_exc = [e["slm_p"] for e in (exc_cook, exc_top, exc_hok)]; sem_exc = [e["sem_p"] for e in (exc_cook, exc_top, exc_hok)]
R_O1 = (f"When each of the five temperature indicators was entered in a separate multivariable model, the cold month ratio was the only indicator with a significant association (standardized β = {f(IND[0]['std_beta'],2,True)}; HC3 {pv(IND[0]['p_hc3'])}; Benjamini–Hochberg-adjusted p = {pnum(IND[0]['p_bh'])}), "
        f"whereas the other indicators were not (HC3 p values of {', '.join(pnum(i['p_hc3']) for i in ind_other)} for mean annual temperature, winter mean temperature, temperature variability, and annual temperature range, respectively) (Supplementary Table S2).")
R_O2 = (f"Excluding the {n_over} prefectures with Cook’s distance >4/n, excluding the most influential prefecture, or excluding Hokkaido and Okinawa did not remove the OLS association (HC3 p values of {pnum(exc_cook['p_hc3'])}, {pnum(exc_top['p_hc3'])}, and {pnum(exc_hok['p_hc3'])}, respectively), "
        f"and no single-prefecture exclusion did so (leave-one-out p values of {pnum(SENS['loo']['p_min'])} to {pnum(SENS['loo']['p_max'])}). In these analyses, the p value was {pnum(min(slm_exc))} to {pnum(max(slm_exc))} in the spatial lag model and {pnum(min(sem_exc))} to {pnum(max(sem_exc))} in the spatial error model (Supplementary Table S3).")
g = {(r["outcome"], r["exposure"], r["covariates"]): r for r in GRID}
def gg(o, e, c): return g[(o, e, c)]
O_T, O_ALL, O_214 = "tablets, 5 categories (primary)", "all units, 5 categories (original definition)", "tablets, category 214"
E_P, E_F5, E_F10 = "<5°C, 2016-2020 (primary)", "<5°C, FY2023", "<10°C, FY2023"
C_P, C_O = "year-aligned (primary)", "original covariates"
all_slm = all(r["selected"] == "SLM" for r in GRID)
sel_ps = [r["selected_p"] for r in GRID]
R_O3 = (f"The OLS association was similar when all units were summed (standardized β = {f(gg(O_ALL,E_P,C_P)['std_beta'],2,True)}; {pv(gg(O_ALL,E_P,C_P)['ols_hc3_p'])}), when only category 214 was analysed ({f(gg(O_214,E_P,C_P)['std_beta'],2,True)}; {pv(gg(O_214,E_P,C_P)['ols_hc3_p'])}), "
        f"when the cold month ratio of fiscal year 2023 alone was used ({f(gg(O_T,E_F5,C_P)['std_beta'],2,True)}; {pv(gg(O_T,E_F5,C_P)['ols_hc3_p'])}), and with the covariates of the initial analysis ({f(gg(O_T,E_P,C_O)['std_beta'],2,True)}; {pv(gg(O_T,E_P,C_O)['ols_hc3_p'])}). "
        f"In contrast, defining the cold month as a month below 10°C in fiscal year 2023 alone showed no association (standardized β = {f(gg(O_T,E_F10,C_P)['std_beta'],2,True)}; {pv(gg(O_T,E_F10,C_P)['ols_hc3_p'])}). "
        f"{'In all 24 specifications the rule preferred the spatial lag model, in which' if all_slm else 'In the model selected by LM diagnostics,'} the p value of the exposure ranged from {pnum(min(sel_ps))} to {pnum(max(sel_ps))} (Supplementary Table S4).")
_RA, _RB = R3["A_primary_covariates"], R3["B_without_aging"]
R_O3B = (f"The indirectly age- and sex-standardized outcome (standardized ratios {f(R3['smr_min'],2)}–{f(R3['smr_max'],2)}; correlation with the crude outcome r = {f(R3['r_crude_std'],2)}) showed the same pattern: in OLS, each additional cold month per year was associated with {f(_RA['per_month'])} tablets "
         f"(95% CI {f(_RA['ci_lo'])} to {f(_RA['ci_hi'])}; {pv(_RA['p_hc3'])}); the spatial lag model gave {pv(_RA['sb']['slm_p'])} and the spatial error model {pv(_RA['sb']['sem_p'])}. "
         f"The correlation of the outcome with the aging rate fell from r = {f(R3['r_aging_crude'],2)} to {f(R3['r_aging_std'],2)}. Omitting the aging rate gave {f(_RB['per_month'])} tablets in OLS ({pv(_RB['p_hc3'])}), {f(_RB['slm_pm'])} in the spatial lag model ({pv(_RB['sb']['slm_p'])}), "
         f"and {f(_RB['sem_pm'])} in the spatial error model ({pv(_RB['sb']['sem_p'])}) (Supplementary Table S4).")
cat_by = {c["category"]: c for c in CAT}
def cat_sel_p(c): return c["slm_p"] if c["selected"] == "SLM" else (c["sem_p"] if c["selected"] == "SEM" else c["ols_hc3_p"])
_cs = []
for _c in CAT:
    _cs.append(_c['category'][:3] + ': ' + pnum(cat_sel_p(_c)))
CAT_SEL = ', '.join(_cs)
cat_pos = [c for c in CAT if c["ols_hc3_p"] < 0.05]; cat_ns = [c for c in CAT if c["ols_hc3_p"] >= 0.05]
R_O4 = (f"In category-specific analyses of tablets, the OLS association was positive for {lst([c['category'].lower() for c in cat_pos])} (Benjamini–Hochberg-adjusted p values of {', '.join(pnum(c['ols_p_bh']) for c in cat_pos)}, respectively)"
        + (f" but not for {lst([c['category'].lower() for c in cat_ns])} ({pv(cat_ns[0]['ols_hc3_p'])})" if cat_ns else "")
        + f". In the models preferred by the decision rule, the p values were {CAT_SEL} (Supplementary Table S4).")
add_by = {a["model"]: a for a in ADD}
a_vals = [a for a in ADD]
a_ns = [a for a in ADD if a["ols_hc3_p"] >= 0.05]
R_O5 = (f"Adding body mass index, smoking, systolic blood pressure, the share of attendees with systolic blood pressure ≥140 mmHg, or sodium intake to the OLS model gave standardized coefficients of {f(min(a['std_beta'] for a in ADD),2,True)} to {f(max(a['std_beta'] for a in ADD),2,True)}. "
        f"The association remained significant when body mass index, systolic blood pressure, or sodium intake was added but was attenuated and not significant when smoking was added ({f(add_by['+ Smoking (checkup FY2022)']['std_beta'],2,True)}; {pv(add_by['+ Smoking (checkup FY2022)']['ols_hc3_p'])}) "
        f"and when body mass index, smoking, and systolic blood pressure were added together ({f(add_by['+ BMI, smoking, systolic BP']['std_beta'],2,True)}; {pv(add_by['+ BMI, smoking, systolic BP']['ols_hc3_p'])}) (Supplementary Table S5). "
        f"")

# ------------------------------------------------------------------ 考察
D_P80 = (f"In this nationwide ecological study, a longer cold season was associated with a larger number of cardiovascular tablets dispensed per resident in conventional regression: each additional cold month per year corresponded to about {f(pm['beta'],0)} tablets per resident per year "
         f"({f(PR['pct_of_mean_per_month'])}% of the mean). However, the regression residuals were strongly spatially autocorrelated, and the association depended on the spatial specification: it was not statistically significant in the spatial lag model but was significant in the spatial error model, which the LM diagnostics did not clearly distinguish. "
         f"The association was also attenuated after adjustment for smoking and was absent with a 10°C definition of cold months in fiscal year 2023. The aging rate was the most consistent correlate of dispensed quantities. "
         f"These exploratory, hypothesis-generating findings suggest, but do not establish, an association between the length of the cold season and dispensed quantities.")
D_P86 = (f"The cold month ratio was the only temperature indicator that was significantly associated with dispensed quantities after adjustment (Supplementary Table S2). This should be interpreted cautiously because the indicator also had the best fit in the initial analysis and because it is itself strongly spatially clustered "
         f"(Moran’s I = {f(SP['moran_x']['I'],2)}), reflecting a north–south gradient shared with many other regional characteristics. "
         f"Whether the duration of cold-season exposure is more relevant to regional pharmaceutical demand than average temperature alone could not be tested formally.")
D_P88 = ("In Japan, these pathways may be amplified by indoor cold exposure and housing conditions. Studies of home temperature, platelet count, blood pressure, and housing type suggest that cold homes can increase cardiovascular stress, particularly among older adults.{ref:umishio2019,saeki2017,tabara,umishio2025} "
         "Because housing insulation and heating practices differ across prefectures, outdoor cold exposure measured at weather stations may misclassify the indoor cold exposure of residents. "
         "Dispensed quantities capture demand at the prefectural level rather than disease onset in individual residents, so the association can be regarded, at most, as a possible health-services signal.")
D_P91 = (f"Aging rate was strongly associated with dispensed quantities (β = {f(aging_c['beta'],2,True)} tablets per resident per year per percentage point; {pv(aging_c['p_hc3'])}). This is consistent with the higher prevalence of cardiovascular risk factors and medication use among older adults, "
         "and with the concentration of the burden of ischemic heart disease and stroke in an aging population in Japan.{ref:gbd} "
         "Ogata et al. used a microsimulation to quantify the contributions of cardiovascular risk factors to national cardiovascular disease trends in Japan.{ref:ogata}")
D_P92 = ("Because the published tables do not allow direct age- and sex-standardization of the outcome, the primary analysis used per-resident quantities and included the aging rate as a covariate; an indirectly standardized outcome gave the same pattern of results (Supplementary Table S4), although residual confounding by age structure may remain.")
D_P93 = ("Dispensing data may also reflect regional differences in treatment practice: Iwabe et al. (approximately 1.32 million insured individuals aged 40–74 years starting antihypertensive treatment) found substantial prefectural variation in blood pressure control.{ref:iwabe} "
         "Higher dispensed quantities may therefore reflect a mixture of disease burden, treatment intensity, medication combinations, and clinical follow-up patterns.")
D_P95 = (f"Unemployment rate was not significantly associated with dispensed quantities in the primary model (β = {f(unemp_c['beta'],1,True)} tablets per resident per year per percentage point; {pv(unemp_c['p_hc3'])}). "
         "Unemployment is nonetheless relevant background, because socioeconomic deprivation has been linked to cardiovascular risk: Roelfs et al. reported in a meta-analysis that unemployment was associated with a 63% higher risk of all-cause mortality,{ref:roelfs} "
         "and Dupre et al. found that the risk of acute myocardial infarction increased with cumulative unemployment episodes (hazard ratio 1.22 for one episode to 1.63 for four or more).{ref:dupre}")
D_P96 = ("In Japan, Miyazaki et al. (71,501 participants, approximately 19 years of follow-up in the JACC Study) reported that among unemployed individuals, a high level of ikigai (purpose in life) was associated with lower cardiovascular mortality "
         "(multivariable hazard ratio 0.69 for men and 0.77 for women), but not among employed individuals.{ref:miyazaki} “Unemployed” in that study refers to employment status at baseline and may include retirees, "
         "so these findings should not be read as a mechanism linking job loss to medication use.")
D_P97 = ("At the ecological level, spatial analyses in Japan have reported associations between area-level deprivation and cardiovascular mortality or hypertension-related risk factors.{ref:okui2020,okui2022} "
         "The tables used here exclude claims paid with public expenditure, which would include medical assistance under public assistance, so the prescriptions of people receiving public assistance are probably not captured; "
         "this may bias any association with unemployment or deprivation.")
D_P98H = "Spatial Dependence and Model Dependence"
D_P99 = (f"Because the OLS residuals remained spatially autocorrelated, the OLS standard errors are likely to be too small, "
         f"and the spatially smooth cold month ratio may partly stand in for unmeasured regional characteristics. The result depended on the specification: the association was not significant in the spatial lag model, which the rule preferred, but was in the spatial error model, and the robust LM tests did not distinguish them. "
         f"We therefore regard the evidence for an independent association as weak.")
D_P100H = "Possible Health-System Implications"
D_P101 = ("If the association observed here were confirmed in longitudinal and individual-level studies, climate indicators might contribute to seasonal blood pressure monitoring, medication stock management, and primary-care follow-up in cold-climate prefectures. "
          "At present, the findings are best viewed as hypothesis-generating.")
D_P102 = ("Whether housing insulation reduces cardiovascular risk and drug use was not examined here and remains a hypothesis; Japanese housing studies link indoor cold exposure and poor insulation to higher blood pressure and cardiovascular risk, and modeling suggests potential health and economic benefits.{ref:umishio2019,saeki2017,tabara,umishio2025,umishio2024}")
D_P103 = ("Projections of non-optimal temperature-related morbidity in Japan suggest that climate and population aging should be considered together in health-system planning.{ref:ohashi,yuan}")
D_P107 = ("Strengths include the use of NDB Open Data covering nearly all claims in Japan, all 47 prefectures, an outcome restricted to a single unit of measurement, and covariates aligned with the outcome year. "
          "All five temperature indicators, several exposure definitions, influential observations, and spatial dependence were evaluated and reported, including analyses that did not support the primary finding.")
D_LIM_H = "Limitations"
D_LIM = ("Several limitations should be considered. First, as an ecological study, the findings are subject to ecological fallacy; associations at the prefectural level cannot be assumed to apply to individuals,{ref:rothman} and the cross-sectional design precludes causal inference. "
         "Second, the outcome is the number of tablets in the published NDB tables, not the number of prescriptions, patients, or defined daily doses; tablets of different drugs are not equivalent doses, the tables list a limited number of products per category, masked cells were not imputed, "
         "direct age- and sex-standardization was not possible, and doses were not standardized (defined daily doses were not analysed). Third, prefecture attribution reflects the location of the dispensing pharmacy or medical institution rather than the patient’s residence. "
         "Fourth, the exposure was measured at one station per prefecture, for 2016–2020 rather than the outcome year, and does not capture indoor temperature. Fifth, the primary exposure was designated with knowledge of its fit in the initial analysis, and most sensitivity analyses were not corrected for multiplicity, so the findings are exploratory. "
         "Sixth, the results depend on the specification of spatial dependence, the weights matrix was based on prefecture centroids, and the LISA clusters were not corrected for multiple testing. Seventh, residual confounding by diet, smoking, indoor heating, air pollution, medication adherence, prescribing practice, and unmeasured regional characteristics cannot be excluded; "
         "the checkup-based covariates are limited to attendees aged 40–74 years, and the unemployment rate is a model-based estimate. Eighth, claims paid with public expenditure are not included. Ninth, a single year of outcome data was analysed; seasonal and longitudinal variation were not examined.")
D_P111 = (f"In this exploratory nationwide ecological study, a longer cold season was associated with a larger number of cardiovascular tablets dispensed per resident in conventional regression (about {f(pm['beta'],0)} tablets per resident per year for each additional cold month per year), together with a higher aging rate. "
          f"The association was not significant in the spatial lag model (but was in the spatial error model, which the LM diagnostics did not clearly distinguish), was attenuated after adjustment for smoking, and was not found with a 10°C definition of cold months, so its robustness is limited.")
D_P112 = ("These findings are hypothesis-generating rather than a measure of individual disease occurrence or of a causal effect of climate. Individual-level and longitudinal studies, including multi-year panel analyses, are needed.")

TAB_NOTE2 = "* <i>p</i> < 0.05; ** <i>p</i> < 0.01; *** <i>p</i> < 0.001. Tablets = cardiovascular tablets dispensed per resident per year; Cold Ratio = cold month ratio (proportion of 60 months, 2016–2020, with mean temperature <5°C); Temp. = mean annual temperature (°C); Unemp. = unemployment rate (%)."
TAB3_TITLE = "Table 3. Univariable OLS Regression: Temperature Indicators and Dispensed Cardiovascular Tablets per Resident per Year (N = 47)"
TAB3_NOTE = "β = change in tablets per resident per year per unit of the indicator (the cold month ratio per 1.0 unit; temperature indicators per °C); conventional standard errors. <b>Bold</b> indicates <i>p</i> < 0.05."
TAB4_TITLE = "Table 4. Multivariable OLS Regression: Dispensed Cardiovascular Tablets per Resident per Year (N = 47)"
TAB4_NOTE = (f"β = change in tablets per resident per year. The cold month ratio is per 1.0 unit; one additional cold month per year corresponds to a ratio increase of 1/12 (β = {f(pm['beta'])}; 95% CI {f(pm['ci_lo'])} to {f(pm['ci_hi'])}) and one SD ({f(psd['sd_x'],3)}) to β = {f(psd['beta'])}. "
             f"R² = {f(PR['r2'],3)}, adjusted R² = {f(PR['adj_r2'],3)}, F = {f(PR['F'],1)} (<i>p</i> < 0.001). Maximum VIF = {f(max(PR['vif'].values()))}; Shapiro-Wilk {pv(PR['sw_p'])}; Breusch-Pagan {pv(PR['bp_p'])}. "
             f"SE, 95% CI, and <i>p</i> values are HC3-robust (normal approximation). <b>Bold</b> indicates <i>p</i> < 0.05.")
TAB5_TITLE = "Table 5. Spatial Dependence and Spatial Regression Models (N = 47)"
TAB5_NOTE = ("Estimates are tablets per resident per year for each additional cold month per year. Spatial weights: k = 4 nearest neighbors of prefecture centroids (great-circle distance), symmetrized and row-standardized. "
             "LM = Lagrange multiplier test on the OLS residuals; the model preferred by the LM decision rule is shown, although the robust LM tests do not clearly distinguish the lag and error models. Moran’s I permutation p values are based on 999 permutations (minimum 0.001). The spatial lag coefficient excludes feedback through neighboring prefectures; direct, indirect, and total effects include it (intervals from 10,000 simulations).")
FIG1 = ("Figure 1. Prefecture-level maps of (A) the cold month ratio (proportion of 60 months from 2016 to 2020 with mean temperature below 5°C at the prefecture’s Japan Meteorological Agency station) and "
        "(B) the number of cardiovascular tablets dispensed per resident in fiscal year 2023 (five drug categories; outpatient prescriptions dispensed outside medical institutions; 10th NDB Open Data).")
FIG2 = ("Figure 2. Diagnostics for the primary ordinary least squares model. (A) Unadjusted relation between the cold month ratio and dispensed tablets per resident; the line is the unadjusted regression line. "
        "(B) Cook’s distance of each prefecture on a logarithmic scale; the dashed line shows 4/n, and prefectures above it are highlighted and labelled. (C) Normal Q–Q plot of the OLS residuals.")
FIG3 = ("Figure 3. Spatial dependence of dispensed tablets per resident. (A) Moran scatter plot (k = 4 nearest neighbors). (B) Local indicators of spatial association (LISA) clusters at <i>p</i> < 0.05: High-High, Low-Low, and not significant (n.s.).")

# ------------------------------------------------------------------ 表
def tab1_rows():
    def row(label, unit, key, nd):
        d = D[key]; return [label, unit, f(d["mean"], nd), f(d["sd"], nd), f(d["min"], nd), f(d["max"], nd)]
    return [["Variable", "Unit", "Mean", "SD", "Min", "Max"],
            row("Dispensed cardiovascular tablets", "tablets per resident per year", "y", 1),
            row("Cold month ratio (<5°C)", "proportion of 60 months", "x", 2),
            row("Cold months per year", "months", "cold_months_per_year", 2),
            row("Mean annual temperature", "°C", "orig_Mean_Temp_avg", 2),
            row("Physicians in medical facilities per 100,000", "per 100,000", "physicians_per100k_2022", 2),
            row("Unemployment rate", "%", "unemployment_pct_2023", 2),
            row("Aging rate (≥65 years)", "%", "aging_pct_2023", 2),
            row("Per capita income", "×10,000 yen", "income_10000yen_FY2022", 2)]

def tab2_rows():
    lab = ["Tablets", "Cold Ratio", "Temp.", "Physicians", "Unemp.", "Aging", "Income"]
    long = ["Dispensed tablets", "Cold month ratio", "Mean temperature", "Physicians per 100,000", "Unemployment rate", "Aging rate", "Per capita income"]
    rows = [["Variable"] + lab]
    for i, a in enumerate(corr_cols):
        r = [long[i]]
        for j, b in enumerate(corr_cols):
            r.append("1.000" if i == j else f"{f(CR[i][j],3)}{stars(CP[i][j])}")
        rows.append(r)
    return rows

def tab3_rows():
    order = ["x", "orig_Mean_Temp_avg", "orig_Winter_temp_avg", "orig_Temp_std", "orig_Temp_range_annual"]
    names = {"x": "Cold month ratio (<5°C)", "orig_Mean_Temp_avg": "Mean annual temperature", "orig_Winter_temp_avg": "Winter mean temperature", "orig_Temp_std": "Temperature variability (SD)", "orig_Temp_range_annual": "Annual temperature range"}
    rows = [["Temperature indicator", "β", "R²", "p"]]
    for c in order:
        u = next(x for x in uni if x["col"] == c)
        rows.append([names[c], f(u["beta"], 1, True), f(u["r2"], 3), pnum(u["p"]).replace("<0.001", "< 0.001")])
    return rows

def tab4_rows():
    rows = [["Variable", "β", "SE (HC3)", "95% CI", "p (HC3)"]]
    order = ["Intercept", "Cold month ratio", "Physicians per 100,000", "Unemployment rate (%)", "Aging rate (%)", "Per capita income (10,000 yen)"]
    show = {"Unemployment rate (%)": "Unemployment rate", "Aging rate (%)": "Aging rate", "Per capita income (10,000 yen)": "Per capita income"}
    for t in order:
        c = co[t]; nd = 3 if abs(c["beta"]) < 1 else (2 if abs(c["beta"]) < 10 else 1)
        rows.append([show.get(t, t), f(c["beta"], nd, True), f(c["se_hc3"], nd), f"{f(c['ci_lo'], nd)} to {f(c['ci_hi'], nd)}", pnum(c["p_hc3"]).replace("<0.001", "< 0.001")])
    return rows

def tab5_rows():
    return [["Statistic", "Value"],
            ["Moran’s I, dispensed tablets per resident", f"{f(SP['moran_y']['I'],3)} (z = {f(SP['moran_y']['z'],2)}; p ≤ 0.001)"],
            ["Moran’s I, cold month ratio", f"{f(SP['moran_x']['I'],3)} (p ≤ 0.001)"],
            ["Moran’s I, OLS residuals", f"{f(B4['moran_res'][0],3)} (p {'< 0.001' if B4['moran_res'][2] < 0.001 else '= ' + f(B4['moran_res'][2],3)})"],
            ["LM test, spatial lag", f"{f(B4['lm_lag'][0],2)} (p {'< 0.001' if B4['lm_lag'][1] < 0.001 else '= ' + f(B4['lm_lag'][1],3)})"],
            ["LM test, spatial error", f"{f(B4['lm_err'][0],2)} (p {'< 0.001' if B4['lm_err'][1] < 0.001 else '= ' + f(B4['lm_err'][1],3)})"],
            ["Robust LM test, spatial lag", f"{f(B4['rlm_lag'][0],2)} (p = {f(B4['rlm_lag'][1],3)})"],
            ["Robust LM test, spatial error", f"{f(B4['rlm_err'][0],2)} (p = {f(B4['rlm_err'][1],3)})"],
            ["Model preferred by the LM decision rule (neither robust LM test significant at 5%)", SEL.capitalize()],
            ["OLS (HC3), per additional cold month per year", f"{f(pm['beta'],2)} (95% CI {f(pm['ci_lo'],2)} to {f(pm['ci_hi'],2)}; p = {f(PR['p_hc3'],3)})"],
            ["Spatial lag model, regression coefficient per additional cold month per year", f"{f(slm_pm,2)} (95% CI {f(slm_lo,2)} to {f(slm_hi,2)}; p = {f(B4['slm_p'],3)}); ρ = {f(B4['slm_rho'],2)}"],
            ["Spatial lag model, average direct / indirect / total effect (95% simulation interval)", f"{f(E4['direct']['est'],2)} ({f(E4['direct']['lo'],2)} to {f(E4['direct']['hi'],2)}) / {f(E4['indirect']['est'],2)} ({f(E4['indirect']['lo'],2)} to {f(E4['indirect']['hi'],2)}) / {f(E4['total']['est'],2)} ({f(E4['total']['lo'],2)} to {f(E4['total']['hi'],2)})"],
            ["Spatial error model, per additional cold month per year", f"{f(sem_pm,2)} (95% CI {f(sem_lo,2)} to {f(sem_hi,2)}; p = {f(B4['sem_p'],3)}); λ = {f(B4['sem_lam'],2)}"],
            ["Spatial weights", "KNN (k = 4), great-circle distance between centroids, symmetrized, row-standardized"],
            ["Sensitivity to k = 3–6 (p of the cold month ratio)", f"Spatial lag {pnum(slm_p_rng[0])}–{pnum(slm_p_rng[1])}; spatial error {pnum(sem_p_rng[0])}–{pnum(sem_p_rng[1])}"]]
