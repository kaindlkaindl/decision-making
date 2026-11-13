# pacman-contest

This repository adds a single file for "easy" competition running, on top of the `pacman-contest` project in the extensive repository by [Sebastian Sardina et al.](https://github.com/AI4EDUC/pacman-contest-3)  While Sardina has a method for running a competition on multiple systems in [another repository](https://github.com/AI4EDUC/pacman-contest-cluster), this is more complicated than neccessary to use when running on a single system.  The Python-file we supply should be easier to use, and integrates with other [HvA](https://hva.nl) solutions.

## Table of contents

1. [About this repository](#what-does-this-repo-provide-exactly)
2. [Requirements](#requirements)
3. [Optional: set up downloading and uploading](#set-up-secrets-file-and-associated-flows)
4. [Optional: cron](#set-up-daily-runs)
5. [To-do before teaching again](#what-should-be-done-for-next-year)

## What does this repo provide, exactly?

This repo provides a single file [`competition.py`](competition.py) that will run a round-robin tournament.  Calling `python3 competition.py -h` will show what all the options are.

In summary, when all optional processes are activated, the program flow structure is:

1. Load the [secrets file](#set-up-secrets-file-and-associated-flows).
2. *Optional, with parameter `-d`:* Download student data.
3. Import student files, and report on disqualifying files.  
4. *Optional, with parameter `-b`:* Recreate `baselineTeam.py` to protect against student overwrites.
5. *Optional, with parameter `-p`:*
   1. Make every team play against each other (a [round-robin](https://en.wikipedia.org/wiki/Round-robin_tournament) tournament).
   2. Record all replay files.
   3. Write a `scoreboard.html` file.
6. *Optional, with parameter `-m`:* Send a message, including a zip of all log files, all replay files and `scoreboard.html`.

## Requirements

As all other parts of [Sardina's original repo](https://bitbucket.org/ssardina-teaching/pacman-projects/), this repo requires a fully-working Python 3.11 installation.

On top of that, access to the following services are required:

- If you want to automatically download new student hand-ins: a SharePoint environment where you can "Request for files" ("Verzoek om bestanden" in Dutch).  This might have to be requested from a system administrator, and relevant Microsoft Flows.
- If you want to automatically upload the zip of all results, and notify staff and students of new results: a Teams team to which all relevant staff and students have access, and relevant Microsoft Flows.
- If you want to run the competition daily automatically, I'd suggest using [cron](https://en.wikipedia.org/wiki/Cron).

## Set up secrets file and associated Flows

Only when you want to automatically download student files, or automatically notify students about results, you need some setup work.  **If you do not intend to use any of this functionality, you do not need to provide a secrets file.**  For this, we use several Microsoft Flow processes, most related to a name used in the secrets file, and to a flag of `competition.py`.

To set up a secrets file, run `python3 competition.py -S` (optionally with `-s YOUR_SECRETS_FILE`), and provide the required information.  Each Flow process has its own URL, that can be found in the editing interface of the trigger action.  If you don't intend to use thhe associated command line flag, you don't have to provide a URL for that secret.

A more in-depth description of each Flow will be documented later.

| Flow secrets name             | Used by flag     | Description                                                            |
|-------------------------------|------------------|------------------------------------------------------------------------|
| *No secrets name*             | *No flag*        | When students upload their work, move to it to a canonical named file. |
| `flow_latest_modified`        | `--download`     | Returns timestamp of latest student upload.                            |
| `flow_create_student_chunks`  | `--download`     | Prepare download of student data on the cloud-side.                    |
| `flow_transfer_student_chunk` | `--download`     | Cloud sends student data in chunks to `competition.py`-device.         |
| `flow_transfer_results_chunk` | `--send-message` | Cloud receives zip of results in chunks.                               |
| `flow_notify`                 | `--send-message` | Posts a message to the Teams environment.                              |

### Set up daily runs

To run a competition every so often automatically, I used [cron](https://en.wikipedia.org/wiki/Cron) on a Linux system. I will explain how to set up cron to run every night at 03.00.

**Notes on choosing how often to compute:**  The teams play in a round-robin tournament: every team faces each other team onces.  For *n* teams, that means there will be *n(n-1)/2* games played.  The system is set up to run one game per hardware threads.  So, roughly speaking, the complete `competition.py` runtime increases quadratically by increasing the number of participating teams *n*, and linearly decreases with the number of number threads.  Make some test runs to see how long computation time on your platform will be.  Take an additional margin of 1 hour between two runs to be sure that there will be no overlapping runs.

You tell cron on which minute (0-59), hour (0-23), day of the month (1-31), month (1-12), and/or day of week (0-6, with 0 = Sunday) some command needs to run.  For each of the datetime values, you can also supply a wildcard symbol `*`, indicating you don't care about that value.  You tell this to cron by calling `crontab -e` (with the `-e` for editing) on the command line, and adding lines.  The lines starting with a `#` are comments.  As always, you are encouraged to comment your work :grimacing:

In this example, the absolute path to `competition.py` is `/home/pkok/pacman-competition-3/competition.py`, and I have decided to run the code every 3 hours from midnight.  Before running the competition, I want to download new student data, which is option `--download` or `-d`.  To be sure no student file overrides the baselineTeam, I want to `--add-baseline`, or `-b`.  To play all matches, I have to provide option `--play-matches` or `-p`.  I also want the students to be notified when results are available, which is done with option `--send-message` or `-m`.  Finally, I don't want any printing to be done to this terminal, which is handled by option `--quiet` or `-q`.

Start by calling `crontab -e` on the command line.  Add the following lines to the end of the open files:

```cron
0  0 * * * cd /home/pkok/pacman-competition-3; python3 competition.py --download --add-baseline --play-matches --send-message --quiet
0  3 * * * cd /home/pkok/pacman-competition-3; python3 competition.py --download --add-baseline --play-matches --send-message --quiet
0  6 * * * cd /home/pkok/pacman-competition-3; python3 competition.py --download --add-baseline --play-matches --send-message --quiet
0  9 * * * cd /home/pkok/pacman-competition-3; python3 competition.py --download --add-baseline --play-matches --send-message --quiet
0 12 * * * cd /home/pkok/pacman-competition-3; python3 competition.py --download --add-baseline --play-matches --send-message --quiet
0 15 * * * cd /home/pkok/pacman-competition-3; python3 competition.py --download --add-baseline --play-matches --send-message --quiet
0 18 * * * cd /home/pkok/pacman-competition-3; python3 competition.py --download --add-baseline --play-matches --send-message --quiet
```

Afterwards, save and close the file.

With these lines we have said: "on any day of the week, in any month, on any day of the month, if it is 0:00, 3:00, 6:00, 9:00, 12:00, 15:00 or 18:00, execute `competition.py` with the desired command line arguments from its own folder.

Remember to remove these lines when the tournament is over!

## What should be done for next year?

Always check if [the repository we forked from](https://github.com/AI4EDUC/pacman-contest-3) has new updates!
