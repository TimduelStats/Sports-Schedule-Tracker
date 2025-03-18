from datetime import datetime
import pytz
import json
from config import  BUCKET_NAME, SCHEDULE_FILENAME, SCHEDULE_PATH
from s3_uploader import upload_to_s3, delete_from_s3
import mlbstatsapi
import logging
from pydantic import BaseModel, ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class GameInfo(BaseModel):
    date: str
    away_team: str
    home_team: str
    venue: str
    time: str


class MLBAPI:
    mlb = mlbstatsapi.Mlb()

    def __init__(self):
        self.mlb = mlbstatsapi.Mlb()
        self.est_tz = pytz.timezone('US/Eastern')

    def get_schedule(self):
        try: 
            current_date = self.get_current_est_date()
            schedule = self.mlb.get_schedule(current_date)
            if not schedule.dates or not current_date:
                logger.error("No schedule found for today.")
                return []
            
            dates = schedule.dates
            game_info_list = []
            for date in dates:
                for game in date.games:
                    game_info = {
                        'date': game.gamedate,
                        'away_team': game.teams.away.team.name,
                        'home_team': game.teams.home.team.name,
                        'venue': game.venue.name,
                        'time': self.convert_utc_to_est(game.gamedate)
                    }

                    try:
                        validated_game_info = GameInfo(**game_info)
                        game_info_list.append(validated_game_info.model_dump())
                    except ValidationError as e:
                        logger.error(f"Error validating game info: {str(e)}")
            return game_info_list
        except Exception as e:
            logger.error(f"Error fetching schedule: {str(e)}")
            return []

    def save_schedule(self, data, filename="/tmp/mlb_schedule.json"):
        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving schedule: {str(e)}")

    def get_current_est_date(self):
        return datetime.now(self.est_tz).strftime('%Y-%m-%d')

    def convert_utc_to_est(self, utc_time_str):
        est = pytz.timezone('US/Eastern')
        # Parse the UTC time string to a datatime object
        utc_time = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%SZ')
        # Set the timezone information for naive datetime object
        utc_time = pytz.utc.localize(utc_time)
        # Convert to EST
        est_time = utc_time.astimezone(est)
        return est_time.strftime("EST %H:%M")
    
def main(event, lambda_context):
    mlb_api = MLBAPI()  
    try:
        # delete old schedule
        logger.info("Deleting old schedule from S3...")
        delete_from_s3(BUCKET_NAME, SCHEDULE_FILENAME)

        logger.info("Fetching new MLB schedule...")
        schedule_data = mlb_api.get_schedule()

        if not schedule_data:
            logger.warning("No schedule data found.")
            return
        
        logger.info("Saving schedule data...")
        mlb_api.save_schedule(schedule_data)

        logger.info("Uploading schedule to S3...")
        upload_to_s3(SCHEDULE_PATH, BUCKET_NAME, SCHEDULE_FILENAME)

        logger.info("Schedule fetched and saved successfully.")
    except Exception as e:
        logger.error(f"Error fetching MLB schedule: {str(e)}")

if __name__ == "__main__":
    main(event=None, lambda_context=None)
