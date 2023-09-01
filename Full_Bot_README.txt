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


*** Credentials ***
Postgresql database credentials provided in .env file,
screened data will be stored in scanned_data table and trades data will be stored in trades_data_all table

*** Parameters  ***
Provide parameters in main_2.py file as specified in it


*** How To Run ***
Make sure IB TWS is open and running so bot can connect with it

Option 1:
    To run using pycharm:

    set main_2.py located in main folder in pycharm configuration and click on run button to run program

Option 2:
    To run using terminal:

    run following commands from command prompt/terminal

    for MacOs/Linux:
          cd < project directory>           # move to project directory
          source venv/bin/activate         # activate virtual environment
          python main_2.py   # Run program

    for windows:
           cd < project directory>           # move to project directory
           venv\Scripts\activate            # activate virtual environment
           main_2.py           # Run program


*** metrics ***

set metrics.py located in main folder in pycharm configuration and click on run button to generate metrics

each trade will be stored in database and you can run metrics.py which will generate trade_results.xlsx file,
which will contain records of all closed positions


*** logs ***

Each run will create date wise log files inside logs folder showing all details of screening+trading


