# This file contains all functies that are applicable to the making of the different XML files
# Specific functions can be found in the xml_<website>.py file 

# Import all necessary modules
import pandas as pd # for easy dataformatting and conversions
from datetime import datetime # to make date conversions
import os # to join directories and filenames
from lxml import etree

def read_course_information(directory, filename):
    """
    This function will read the database file and returns the course information of all courses in a pandas dataframe.
    ! Every value will be read as a string
    """
    course_information = pd.read_excel(os.path.join(directory, filename),
                                       sheet_name = 'cursussen',
                                       dtype=str,
                                       usecols = ['CursusID', 'Cursusnaam', 'Omschrijving', 'Prijs',
                                                  'Extra_kosten', 'Omschrijving_extra_kosten', 'Duur', 
                                                  'Duur_eenheid', 'URL', 'PDF_URL'])
    course_information.fillna(0, inplace = True)

    return course_information

def read_course_planning(directory, filename):
    """ 
    This function will read the database file and returns the planning of the courses in a pandas dataframe
    ! Every value will be read as a string

    This function will also transform the date and time columns to the right formats for XML (date = yyyy-mm-dd and time  = HH:MM)
    This format is used for the XML in Springest, Edubookers and Studytube
    """
    course_planning = pd.read_excel(os.path.join(directory, filename),
                                    sheet_name = 'planning',
                                    dtype = str)
    
    # Convert date notation
    date_to_datetime = [datetime.strptime(str(course_planning.Datum[idx]), '%d-%m-%Y') for idx in range(len(course_planning))]
    course_planning.Datum = [date_to_datetime[idx].strftime('%Y-%m-%d') for idx in range(len(date_to_datetime))]

    # Convert time notation
    for tijd in ['Begintijd', 'Eindtijd']:
        string_to_datetime = [datetime.strptime(str(course_planning.loc[idx, tijd]), '%H:%M:%S') for idx in range(len(course_planning))]
        course_planning[tijd] = [string_to_datetime[idx].strftime('%H:%M') for idx in range(len(string_to_datetime))]

    return course_planning

def add_product_information(parent, local_ID, information_type, table):
    """
    This function will create nodes with the course information
    """
    new_product_information = etree.SubElement(parent, information_type) # create the new node
    new_product_information.text = str(table[table.ID == local_ID][information_type].values[0]) # indexing based on the unique course ID number

def add_courseday_information(parent, schedule_information, daynumber, table, startday_index):
    """
    This function will create nodes with the course planning information
    """
    new_schedule_information = etree.SubElement(parent, schedule_information) # create the new node
    new_schedule_information.text = str(table.loc[table.RowID == str(int(startday_index) + daynumber), schedule_information].values[0]) # indexing based on the unique RowID

def create_geoict_df(information_df, planning_df):
    geoict_df = pd.DataFrame(columns = ['eventid', 'cursusnaam', 'tekst', 'datum']) # initialisation of the needed dataframe
    # dataframe with month in numbers and letters for conversion
    months = pd.DataFrame({'numbers': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                            'letters': ['januari', 'februari', 'maart', 'april', 'mei', 'juni',
                                        'juli', 'augustus', 'september', 'oktober', 'november', 'december']})

    # an event is defined as every time a course is planned, from the startdate to the enddate
    # so if course1 is planned on 1, 2 and 3 January and again on 1, 2 and 3 February, then this course has two events,
    # where event1 = 1,2,3 January and event2 = 1,2,3 February

    for event_idx in range(len(pd.unique(planning_df.EventID))): # for every event that is in the planning
        event_ID =  pd.unique(planning_df.EventID)[event_idx] # the event ID
        geoict_df.loc[event_idx, 'eventid'] = event_ID # fill in the event ID in the geoict dataframe

        course_ID = planning_df.loc[planning_df.EventID == event_ID, 'CursusID'].values[0] # the course ID
        event_place = planning_df.loc[planning_df.EventID == event_ID, 'Locatie'].values[0] # the place where the course is given

        cursusnaam =  information_df.loc[information_df.CursusID == course_ID, 'Cursusnaam'].values[0] # the coursename
        geoict_df.loc[event_idx, 'cursusnaam'] = cursusnaam # fill in the coursenames in the geoict dataframe

        datums = planning_df.loc[planning_df.EventID == event_ID, 'Datum'].tolist() # all dates of this event in a list

        geoict_df.loc[event_idx, 'datum'] = datums[0] # the 'datum' in the geoict dataframe is the startdate, so the first date in the list

        datums = [datetime.strptime(datum, "%Y-%m-%d") for datum in datums] # convert the string dates to datetime objects

        # a list of all months the event is planned in, needed if the event takes place in multiple months, occurs sometimes
        # if the course is very long or it is planned at the end of one month and the start of the next month
        event_maanden = pd.unique([str(int(datum.strftime("%m"))) for datum in datums])

        if len(event_maanden) == 1: # als alle dagen in dezelfde maand vallen
            # the str(int()) combination is used multiple times to make sure the 01-09 numbers as used in the datetime objects are written as 1-9 numbers
            days_string = ', '.join([str(int(datum.strftime("%d"))) for datum in datums]) # join all days to one string
            month = months.loc[months.numbers == int(datums[-1].strftime("%m")), 'letters'].values[0] # get the month in letters
            days_string = days_string + " " + str(month) # combine the days-string with the month
            tekst = cursusnaam + ": " + days_string # combine the coursename with the days and the month to get the string that is needed

        else: # if the course takes place in multiple months, something else needs to happen
            days_string = "" # make an empty string for initialisation

            for m in event_maanden: # for every month that the event is planned in...
                datums_subset = [datum for datum in datums if str(int(datum.month)) == m] # make a subset of the dates that are in the current month
                days_string = days_string + ', '.join([str(int(datum.strftime("%d"))) for datum in datums_subset]) # add the days of this subset to the string
                month = months.loc[months.numbers == int(m), 'letters'].values[0] # get the current month in letters
                days_string = days_string + " " + str(month) + " & " # add the month to the string

            tekst = cursusnaam + ": " + days_string[:-3] # if the loop is finished, there is one too many " & " added to the string, so this is removed by using the string up until the last 3 characters
        
        tekst = tekst + " in " + event_place 
        geoict_df.loc[event_idx, 'tekst'] = tekst # fill in the text in the geoict dataframe

    return geoict_df