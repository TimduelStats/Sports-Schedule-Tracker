# Sports Schedule Tracker

The **Sports Schedule Tracker** fetches daily MLB game schedules, processes the data to include relevant game details (like team names, venue, and time in EST), and integrates odds data from the Odds API. The final schedule is saved in JSON format and uploaded to an Amazon S3 bucket.

## Features
- Fetches daily MLB game schedules from the MLB API.
- Processes game data to include team names, venue, and game time (EST).
- Integrates with the Odds API to include game IDs for further use in sports odds tracking.
- Automatically uploads the schedule to Amazon S3.

