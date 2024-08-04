import requests
from datetime import datetime, timedelta, timezone
import pytz
import json
from config import API_KEY, SPORT
from s3_uploader import upload_to_s3, delete_from_s3


class MLBAPI:
    BASE_URL = 'https://statsapi.mlb.com/api/v1/'
    BUCKET_NAME = 'timjimmymlbdata'
    
    @staticmethod
    def get_schedule(sport_id = 1):
        """
        Fetches the schedule for the specified sport.

        Args:
            sport_id (int): The ID of the sport. Defaults to 1 for MLB.

        Returns:
            dict: The JSON response containing the schedule data.

        Raises:
            requests.exceptions.RequestException: If the request fails or returns a bad status code.
        """
        current_date = MLBAPI.get_current_est_date()
        url = f"{MLBAPI.BASE_URL}/schedule/games/?sportId={sport_id}&startDate={current_date}&endDate={current_date}"
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.json()
    
    @staticmethod
    def save_schedule(data, filename="/tmp/mlb_schedule.json"):
        """
        Save the given data to a JSON file.

        Args:
            data (dict): The data to save.
            filename (str): The filename where the data should be saved.
        """
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
    
    @staticmethod
    def process_game_data(data):
        """
        Process the game data to extract relevant information.

        Args:
            game_data (dict): The game data from the API response.

        Returns:
            dict: A dictionary containing the relevant game information.
        """
        games = data.get("dates", [])[0].get("games", [])
        game_info_list = []

        # Get the events from odds api in order to add game id to game_info
        events = MLBAPI.fetch_events()
        
        # extract each game's information
        for game in games:
            game_time_est = MLBAPI.convert_utc_to_est(game['gameDate'])
            game_info = {
                'date': game["gameDate"],
                'time': game_time_est,
                'away_team': game["teams"]["away"]["team"]["name"],
                'home_team': game["teams"]["home"]["team"]["name"], 
                'venue': game["venue"]["name"],
            }
            # Extract game id from api and add to game_info
            for event in events:
                if event['home_team'].lower() == game_info['home_team'].lower():
                    game_info['id'] = event['id']

            game_info_list.append(game_info)
        return game_info_list
    
    def fetch_events():
        """
        Fetch today's MLB events using the Odds API.
        """
        today_str, tomorrow_str = MLBAPI.get_utc_start_and_end()

        response = requests.get(
            f'https://api.the-odds-api.com/v4/sports/{SPORT}/events',
            params={
                'apiKey' : API_KEY,
                'commenceTimeFrom': today_str,
                'commenceTimeTo': tomorrow_str,
                'dateFormat': 'iso'
            }
        )

        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch odds: {response.status_code}, {response.text}")

        return response.json()
    
    @staticmethod
    def get_current_est_date():
        """
        Get the current date in EST.

        Returns:
            str: The current date in EST in YYYY-MM-DD format.
        """
        est = pytz.timezone('US/Eastern')
        now_est = datetime.now(est)
        return now_est.strftime('%Y-%m-%d')

    @staticmethod
    def convert_utc_to_est(utc_time_str):
        """
        Converts a UTC time string to EST time string.

        Args:
            utc_time_str (str): The UTC time string in ISO 8601 format.

        Returns:
            str: The converted EST time string.
        """
        est = pytz.timezone('US/Eastern')

        # Parse the UTC time string to a datatime object
        utc_time = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%SZ')

        # Set the timezone information for naive datetime object
        utc_time = pytz.utc.localize(utc_time)
        
        # Convert to EST
        est_time = utc_time.astimezone(est)

        return est_time.strftime("EST %H:%M")
    
    def get_utc_start_and_end():
        """
        Get the start and end times for today in UTC.

        Returns:
            tuple: A tuple containing the start and end times in ISO 8601 format.
        """
        # Get the current UTC time
        now_utc = datetime.now(timezone.utc)

        # Reset the time to midnight of the start day
        now_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Set the end time to 2 AM of the next day
        end_of_today_utc = now_utc + timedelta(days=1, hours=2)

        # Convert the times to ISO 8601 format
        today_str = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str = end_of_today_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

        return today_str, end_str
    

def main(event, lambda_context):
    try:
        # delete old schedule
        delete_from_s3(MLBAPI.BUCKET_NAME, "mlb_schedule.json")
        schedule_data = MLBAPI.get_schedule()
        games = MLBAPI.process_game_data(schedule_data)
        MLBAPI.save_schedule(games)
        upload_to_s3("/tmp/mlb_schedule.json", MLBAPI.BUCKET_NAME, "mlb_schedule.json")
        print("Schedule fetched and saved successfully.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main(event=None, lambda_context=None)