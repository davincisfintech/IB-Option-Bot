***  Installation ***
if not done already
install python 3.8 for your operating system using this link  https://www.python.org/downloads/

install pycharm community edition using this link  https://www.jetbrains.com/pycharm/download/


*** Setup  ***
if not done already
run following commands from command prompt/terminal

for MacOs/Linux:
      cd < project directory>           # move to project directory
      python -m venv venv              # create virtual environment
      source venv/bin/activate         # activate virtual environment
      pip install -r requirements.txt    # install dependencies

for windows:
       cd < project directory>           # move to project directory
       python -m venv venv              # create virtual environment
       venv\Scripts\activate            # activate virtual environment
       pip install -r requirements.txt     # install dependencies


*** How To Run ***

Option 1:
    To run using pycharm:

    set scrapper.py located in main folder in pycharm configuration and click on run button to run program

Option 2:
    To run using terminal:

    run following commands from command prompt/terminal

    for MacOs/Linux:
          cd < project directory>           # move to project directory
          source venv/bin/activate         # activate virtual environment
          python scrapper.py   # Run program

    for windows:
           cd < project directory>           # move to project directory
           venv\Scripts\activate            # activate virtual environment
           scrapper.py           # Run program


*** logs ***

Each run will create date wise log files inside logs folder showing all details of scrapper

*** How to Compare ***
Scraper will show raw data scrapped + symbol + ticker info + news summary with UTC time as receive time,
scrapped from https://pro.benzinga.com/dashboard so check it for comparison


