# Install packages if not already installed
if (!requireNamespace("readr", quietly = TRUE)) install.packages("readr")
if (!requireNamespace("dplyr", quietly = TRUE)) install.packages("dplyr")

library(readr)
library(dplyr)
library(stringr)
library(dplyr)


# Specify the file path or name
file_name <- '/Users/Luke/Documents/Syracuse/Research/Evacuation/dataverse_files/Full Database/HEvOD_2014-2022.csv'

# Read the CSV file
df <- read_delim(file_name, delim = '|', col_types = cols(`County FIPS` = col_character()), quote = '"', locale = locale(encoding = "UTF-8"))

# Print the first few rows of the dataframe
print(head(df))

# Print columns and datatypes
print(str(df))

sum(df$State == "FL")



# Filter data for 'Hurricane Ian'
hurricane_ian_df <- df %>% filter(`Event Name` == 'Hurricane Ian')
print(hurricane_ian_df)

#upload county-windspeed-storm data
storms_wind<-read.csv("/Users/Luke/Documents/Syracuse/Research/Evacuation/florida_counties_storm_dummy_windspeed.csv")
storms_wind$FIPS<-as.character(storms_wind$FIPS)

#Filter for just florida
hurricane_FL<- df %>% filter(`State` == 'FL')
# Remove the leading word "Hurricane " (and the space after it)
hurricane_FL$`Event Name`<- str_remove(hurricane_FL$`Event Name`, "^Hurricane\\s+")

#rename columns to match storms_wind
hurricane_FL<- hurricane_FL %>% rename(NAME= `Event Name`,
                                       Type = `Order Type`,
                                       Order_Date = `Announcement Date`,
                                        FIPS = `County FIPS`,
                                       Evacuation_Area = `Evacuation Area`)

#make uppercase
hurricane_FL$NAME <- toupper(hurricane_FL$NAME)

#join wind data with evacuation data
df_joined<- storms_wind %>%
  left_join(hurricane_FL, by = c("FIPS", "NAME"))

#create dummies for mandator and voluntary evac, as well as Any_Evac for either type
df_joined <- df_joined %>%
  mutate(Mandatory = ifelse(grepl("Mandatory", Type, ignore.case = TRUE), 1, 0))
df_joined <- df_joined %>%
  mutate(Voluntary= ifelse(grepl("Voluntary", Type, ignore.case = TRUE), 1, 0))
df_joined$Any_Evac = df_joined$Mandatory + df_joined$Voluntary

#load county-level deaths data
deaths<-read.csv("/Users/Luke/Documents/Syracuse/Research/Evacuation/deaths.csv")
deaths<- deaths %>% rename(NAME = Disaster,
                           FIPS= FIPS.Code,
                           Deaths= Number.of.Deaths,
                           SEASON = Year)
deaths$FIPS<-as.character(deaths$FIPS)
deaths$NAME <- toupper(deaths$NAME)

#join deaths with full dataset
df_joined <- df_joined %>%
  left_join(deaths, by = c("FIPS", "NAME"))

#make NAs 0
df_joined$Deaths[is.na(df_joined$Deaths)] <- 0


#cut for positive deaths for experimentation
df_cut<-  df_joined%>%
  filter(Deaths >0)

#filter out no deaths, no evacuation (top left quandrant)
df_filtered <- df_joined %>%
  filter(!(Deaths == 0 & Any_Evac == 0))


#plot; can change x to be deaths or other measure of severity to determine overlap area
ggplot(df_filtered, aes(x = Deaths, y = COUNTYNAME, color = factor(Any_Evac))) +
  geom_point(size = 3) +  # Dots with size 3
  labs(
    title = "Hurricanes and Evacuations",
    x = "Deaths",
    y = "Hurricane Name",
    color = "Any_Evac"
  ) +
  scale_color_manual(values = c("0" = "blue", "1" = "red")) +  # Custom colors
  theme_minimal()

#preliminary analysis 
mod_1<-lm(Deaths ~ Any_Evac + factor(wind_kt), data=df_filtered)
summary(mod_1)

#make panel dataframe with county and storm indices 
df_panel <- pdata.frame(df_filtered, index = c("FIPS", "NAME"))
model_fe <- plm(Deaths ~ Mandatory + factor(wind_kt), data = df_panel, model = "within")
summary(model_fe)

table(index(df_panel), useNA = "ifany")


# Load the installed Package
library(readr)
redfin<-readr::read_tsv("/Users/Luke/Downloads/county_market_tracker.tsv000")

