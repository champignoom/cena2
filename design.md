Cena2 design doc
=======

## Menu

- Files
    - Open contest
    - Close contest
    - Properties
- Contest
    - Participate
    - Host
- Help
    - Manual
    - About

## Dialog: Properties

- Compiler
    - Compile command: `/path/to/g++ -o {name} {name.cpp}`
    - Download gcc
- Default constraints
    - Memory: 512M
    - Time: 1s
    - Total score: 100


## Panel

- Grid. (users) * (problems)
    - Listen to changes of /path/to/contest/src
    - Double click column header to config problems
- Matrix of squares, representing testcases.
  with no more than 20 testcases, there's only one row.
  each testcase is represented as a colored square
    - AC: Green
    - WA: Red
    - RE: Dark red
    - TLE: Yellow
    - MLE: Dark yellow
- Buttons
    - Judge all
    - Judge selected


## Contest

- Participate Contest
    - Name
    - List of servers, (refresh every 5s / instant)
- Host Contest
    - "Tell the participants to access 192.168.999.999 for downloading this judger"
    - List of participants, (refresh every 5s / instant)
    - Distribute files (problems.pdf, samples/)
    - Collect answers
    - End contest

