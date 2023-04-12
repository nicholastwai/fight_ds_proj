'''
convert this into file for local use as feature pipeline so its compatible with github actions
'''
# -*- coding: utf-8 -*-
"""feature_pipeline.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1K8IZ7OG7rcDmecr7jSIvJXlu98fOfUYs

#Installing Data Scraper
"""

#!pip install -e git+https://github.com/nicholastwai/UFC_Data_Scraper.git#egg=UFC_Data_Scraper 

# note to self: must change location of starting_dir = os.getcwd() to line 49 of scraper.py so that starting_dir is initalized before,
# must also reconnect runtime so that changes are registered
# DO NOT REINSTALL OTHERWISE YOU'LL HAVE TO REPEAT ABOVE STEP
# Resolved above issue by forking repo and adding my own changes

"""#Changing to Correct Directory for Data Scraper
- make sure to have file structure specified in data scraper documentation
 already created and Google Drive mounted
"""

# Commented out IPython magic to ensure Python compatibility.
# %cd /content/drive/MyDrive/Capstone\ Project/End-to-End\ ML \Service
#!ls

import pandas as pd  
from UFC_Data_Scraper import scraper as s #Creating instance of Ufc_Data_Scraper object
scraper = s.Ufc_Data_Scraper()

"""# Scraping athlete data and placing in dataframe"""

#import os #this may be necesary to get starting_dir initialized
# getting all fighters
list_of_fighters = scraper.get_all_fighters()
json_fighter_list = s.Ufc_Data_Scraper().fighter_to_Json(list_of_fighters)
athletes_df = pd.DataFrame.from_dict(json_fighter_list).transpose()

"""# Scraping event data and moving it to dataframe"""

#scrape all ufc fights data 
list_of_events =  s.Ufc_Data_Scraper().scrape_all_fights(load_from_dir = False)
event_dict = s.Ufc_Data_Scraper().fights_to_Json(list_of_events)
all_events_df = pd.DataFrame.from_dict(event_dict).transpose()

"""# Data Cleaning
- taking appropriate code from fight_proj_EDA to create dataset
"""

#dropping null rows

indexNullReach = athletes_df[athletes_df['reach']== -1].index #  null reach
athletes_df.drop(indexNullReach, inplace = True)

indexNullStance = athletes_df[athletes_df['stance']== -1].index #  null stance
athletes_df.drop(indexNullStance, inplace = True)

indexNullHeight= athletes_df[athletes_df['height']== '--'].index # null height
athletes_df.drop(indexNullHeight, inplace = True)


# dropping td defense, birthdate, and no_contest columns
athletes_df.drop(columns = ['no_contest', 'DOB', 'takedown_defense', 'name'], inplace = True)

# these features were deemed not useless by random forest feature selector 
athletes_df.drop(columns = ['height', 'weight', 'reach', 'stance', 'sub_average'], inplace = True)

# transforming height feature to inches
heights = athletes_df['height']
height_inches = []

for i in range(heights.size):
  inches = (int(heights[i][0]) * 12) + int(heights[i][1])
  height_inches.append(inches)

athletes_df['height'] = height_inches

# typecasting everything from string to int
athletes_df = athletes_df.apply(pd.to_numeric)


"""# Creating fighter matchups for final fight dataset to train models on"""

df = pd.DataFrame()

for i in range(all_events_df.shape[0]):
  event = all_events_df.iloc[i]
  for j in range(event.size):
    fight = event.iloc[j]
    if fight:
      try:
        s1 = athletes_df.loc[fight['fighter1']]
        s2 = athletes_df.loc[fight['fighter2']]
        s1.index = ['wins1', 'loss1', 'splm1', 'sig_acc1', 'sig_absorbed1', 
                        'sig_strike_defense1', 'average_takedown1', 'takedown_acc1']
        s2.index = ['wins2', 'loss2', 'splm2', 'sig_acc2', 'sig_absorbed2', 
                        'sig_strike_defense2', 'average_takedown2', 'takedown_acc2']
        s3 = pd.concat([s1, s2])
        s3['winner'] = fight['winner']
        df = pd.concat([df, s3], axis = 1)
      except:
        pass
df = df.transpose()


# setting index so that dropping invalid rows by indices works
df.reset_index(inplace=True)
df.drop(inplace = True, columns = ['index'])

#dropping rows where the winner column resulted in an error
for i in range(0, len(df['winner'])):
  if df['winner'][i] == -1:
    df = df.drop([i])

# setting index again after dropping the ones with invalid winner
df.reset_index(inplace=True)
df.drop(inplace = True, columns = ['index'])

# creating index column for Hopsworks primary key
df.reset_index(inplace=True)


"""# Moving data set to feature store (incorporating Hopsworks)"""

import hopsworks
import os
api_key = os.environ['API_KEY']

project = hopsworks.login(api_key_value = api_key)

fs = project.get_feature_store()

#incrementing data version number
if not os.path.exists('version.txt'):
    with open('version.txt','w') as f:
        f.write('0')
with open('version.txt','r') as f:
    version_num = int(f.read())
    version_num +=1 
with open('version.txt','w') as f:
    f.write(str(version_num))

fight_data_fg = fs.get_or_create_feature_group(
    name="fight_data",
    version=version_num,
    description="Fight data for bout outcome prediction.",
    primary_key = ['index'],
)

fight_data_fg.insert(df)

feature_descriptions = [
    {"name": "wins1", "description": "number of wins in fighter 1's record"}, 
    {"name": "loss1", "description": "number of losses in fighter 1's record"}, 
    {"name": "splm1", "description": "significant strikes landed per min by fighter 1"}, 
    {"name": "sig_acc1", "description": "fighter 1's significant strike accuracy"}, 
    {"name": "sig_absorbed1", "description": "fighter 1's significant strikes absorbed per minute"}, 
    {"name": "sig_strike_defense1", "description": "fighter 1's significant strike defense (% of opponent's strikes that did not land)"}, 
    {"name": "average_takedown1", "description": "average number of takedowns attempted per 15 minutes by fighter 1"},
    {"name": "takedown_acc1", "description": "takedown accuracy of fighter 1"},
    {"name": "wins2", "description": "number of wins in fighter 2's record"}, 
    {"name": "loss2", "description": "number of losses in fighter 2's record"}, 
    {"name": "splm2", "description": "significant strikes landed per min by fighter 2"}, 
    {"name": "sig_acc2", "description": "fighter 2's significant strike accuracy"}, 
    {"name": "sig_absorbed2", "description": "fighter 2's significant strikes absorbed per minute"}, 
    {"name": "sig_strike_defense2", "description": "fighter 2's significant strike defense (% of opponent's strikes that did not land)"}, 
    {"name": "average_takedown2", "description": "average number of takedowns attempted per 15 minutes by fighter 2"},
    {"name": "takedown_acc2", "description": "takedown accuracy of fighter 2"},  
]

for desc in feature_descriptions: 
    fight_data_fg.update_feature_description(desc["name"], desc["description"])