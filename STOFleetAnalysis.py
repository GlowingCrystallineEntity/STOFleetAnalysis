from datetime import datetime
from sys import argv
import shutil
import glob
import re
import csv
import statistics as stats

AccountName = ""

# Tacitly assuming these all exist
Root = ""
# Root = "D:/GameInstalls/test"
Pattern = "*.csv"
Copy_Destination = ""
FILE_DATE_PATTERN = "%Y%m%d-%H%M%S"
Field_Names = \
  "Character Name, Account Handle, Level, Class, Guild Rank, Contribution Total, Join Date, Rank Change Date, Last Active Date, Status, Public Comment, Public Comment Last Edit Date"
ROUND_FACTOR = 100
# If true, only display stats for one difference (depending on FROM_START);
#   if false, display stats between every two files (and FROM_START is ignored)
ONE_ONLY = False
# If true, display stats from first file to last file; If false, display stats between every two files; if ONE_ONLY is also
#   true, display stats only between last two files
FROM_START = True
# If false, don't print the "first" of the diff calculation -- either the first file (if FROM_START is True),
#  or the penultimate file (if FROM_START is False).  Ignored if ONE_ONLY is False.
PRINT_FIRST = True

fleetFiles = []

def round(x):
  return int(ROUND_FACTOR * x + 0.5) / ROUND_FACTOR

def roundInt(x):
  return int(x + 0.5)

# From http://stackoverflow.com/questions/715417/converting-from-a-string-to-boolean-in-python
def str2bool(value):
  """
     Converts 'something' to boolean. Raises exception for invalid formats
         Possible True  values: 1, True, "1", "TRue", "yes", "y", "t"
         Possible False values: 0, False, None, [], {}, "", "0", "faLse", "no", "n", "f", 0.0, ...
  """
  if str(value).lower() in ("yes", "y", "true", "t", "1"): return True
  if str(value).lower() in ("no", "n", "false", "f", "0", "0.0", "", "none", "[]", "{}"): return False
  raise Exception('Invalid value for boolean conversion: ' + str(value))


def getVal(dict, key, default):
  if key in dict:
    return dict[key]
  else:
    return default


# Read from config file
filename = "./config.txt"
if len(argv) == 2:
  script, filename = argv

config = {}
with open(filename) as f:
  for line in f:
    stripLine = line.strip()
    if stripLine == "" or stripLine[0] == "#":
      continue
    if stripLine.count("=") != 1:
      print("Must have exactly one \"=\" on non-comment lines")
      exit(1)
    (key, val) = line.strip().split("=")
    config[key.strip()] = val.strip()

ptrn = re.compile("^<.*>$")
AccountName = getVal(config, "AccountName", "")
if AccountName == "" or ptrn.match(AccountName):
  raise Exception("Must define AccountName in file config.txt (or specify config file on command line)")
Root = getVal(config, "Root", Root)
if ptrn.match(Root):
  raise Exception("Must define Root in file config.txt (or specify config file on command line)")
Pattern = getVal(config, "Pattern", Pattern)
Copy_Destination = getVal(config, "Copy_Destination", Copy_Destination)
if ptrn.match(Copy_Destination):
  raise Exception("Must define Copy_Destination in file config.txt (or specify config file on command line)")
FILE_DATE_PATTERN = getVal(config, "FILE_DATE_PATTERN", FILE_DATE_PATTERN)
ROUND_FACTOR = int(getVal(config, "ROUND_FACTOR", ROUND_FACTOR))
ONE_ONLY = str2bool(getVal(config, "ONE_ONLY", ONE_ONLY))
FROM_START = str2bool(getVal(config, "FROM_START", FROM_START))
PRINT_FIRST = str2bool(getVal(config, "PRINT_FIRST", PRINT_FIRST))

# Move CSV Exports out of STO install dir, into a working dir
moveCount = 0
for f in glob.iglob(Root + "/" + Pattern):
  print("Moving:", f, "to:", Copy_Destination)
  shutil.move(f, Copy_Destination)
  moveCount += 1

print("")
print("moved ", moveCount, " files", sep="")
print("")

# Read the filenames, and extract fleet name and export date from them
for f in glob.iglob(Copy_Destination + "/" + Pattern):
  fleetFile = re.split("[/\\\\_.]+", f)
  dt = datetime.strptime(fleetFile[-2], FILE_DATE_PATTERN)
  splitNames = fleetFile[-3:-1]
  splitNames.append(dt)
  splitNames.append(f)
  fleetFiles.append(splitNames)

# sorting by filename implicitly sorts by date
fleetFiles.sort(key=lambda p: p[-1])
shortFleetFiles = []

if ONE_ONLY:
  # Sentinel value in case there's only one file for the last fleet in the list
  fleetFiles.append([""] * len(fleetFiles[0]))
  first = fleetFiles[0]
  last = ["", first]
  for current in fleetFiles:
    # if first[0] != current[0] or current[0] == fleetFiles[-1][0]:
    if first[0] != current[0]:
      if FROM_START:
        shortFleetFiles.append(first)
      elif last[1] != "" and last[1][0] != "":
        shortFleetFiles.append(last[1])
      if last[0] != "" and last[0][0] != "":
        shortFleetFiles.append(last[0])
      else:
        last[0] = current
      first = current
      last = ["", first]
    else:
      last[1] = last[0]
      last[0] = current
else:
  shortFleetFiles = fleetFiles

summary = []

# Read the files, and calculate and print file data
lastFleetName = ""
lastContribTotal = 0
lastFileTime = datetime.min
charName = ""
lastCharContrib = 0
charContrib = 0
for i in range(len(shortFleetFiles)):
  ff = shortFleetFiles[i]
  with open(ff[-1]) as csvfile:
    reader = csv.DictReader(csvfile)
    contribTotal = 0
    data = []
    for row in reader:
      contrib = int(row["Contribution Total"])
      contribTotal += contrib
      data.append(contrib)
      if AccountName == row["Account Handle"]:
        charName = row["Character Name"]
        charContrib = int(row["Contribution Total"])
    members = len(data)
    mu = stats.mean(data)
    median = stats.median(data)
    stdev = stats.pstdev(data, mu)
    zeroCount = data.count(0)
    membersZeroCount = members - zeroCount
    fractionNonZero = membersZeroCount / members
    dataNonZero = [x for x in data if x != 0]
    muNZ = stats.mean(dataNonZero)
    medianNZ = stats.median(dataNonZero)
    stdevNZ = stats.pstdev(dataNonZero, muNZ)
    contribDiff = 0
    contribPerHourPerMemberNZ = 0.
    if lastFleetName != ff[0]:
      print("---")
      if "" != lastFleetName:
        print("")
      if "" != charName:
        print(charName + ":")
      lastContribTotal = contribTotal
      lastFileTime = ff[2]
      lastCharContrib = charContrib
    if PRINT_FIRST or lastFleetName == ff[0] or \
        (i < len(shortFleetFiles) - 1 and shortFleetFiles[i + 1][0] != ff[0]) or i == len(shortFleetFiles) - 1:
      print(ff[0], " ", ff[2], ": ", charName + ": ", "{:,}".format(int(charContrib)),
            ", Contrib Total: ", "{:,}".format(contribTotal), ", Members: ", members,
            ", NonZero: ", "{:,}".format(membersZeroCount), " ({:,.2f}".format(round(fractionNonZero * 100)), "%)",
            sep="")
      print("  mean  : ", "{:,}".format(roundInt(mu)), ", median  : ", "{:,}".format(roundInt(median)),
            ", StdDev  : ", "{:,}".format(roundInt(stdev)), " ({:,.2f}".format(round(stdev / contribTotal * 100)), "%)",
            sep="")
      print("  meanNZ: ", "{:,}".format(roundInt(muNZ)), ", medianNZ: ", "{:,}".format(roundInt(medianNZ)),
            ", StdDevNZ: ", "{:,}".format(roundInt(stdevNZ)), " ({:,.2f}".format(round(stdevNZ / contribTotal * 100)),
            "%)", sep="")
      contribDiff = contribTotal - lastContribTotal
      charContribDiff = charContrib - lastCharContrib
      timeDiff = 0
      contribPerHour = 0
      contribPerHourPerMember = 0
      contribPerHourPerMemberNZ = 0
      charContribPerHour = 0
      if ff[2] > lastFileTime:
        timeDiff = ff[2] - lastFileTime
        contribPerHour = contribDiff / (timeDiff.total_seconds() / 3600)
        contribPerHourPerMember = contribPerHour / members
        contribPerHourPerMemberNZ = contribPerHour / membersZeroCount
        charContribPerHour = charContribDiff / (timeDiff.total_seconds() / 3600)
      print("Char Contrib: ", "{:,}".format(charContribDiff),
            ", Fleet Total Contrib: ", "{:,}".format(contribDiff), " / ", "Time Diff: ", timeDiff, sep="")
      print("Char Contrib Per Hour: ",
            "{:,.2f}".format(round(charContribPerHour)))  # Shouldn't have negative numbers anyway...
      print("Fleet Contrib Per Hour: ", "{:,.2f}".format(round(contribPerHour)),
            ", Per Member: ", round(contribPerHourPerMember), ", Per MemberNZ: ", round(contribPerHourPerMemberNZ),
            sep="")  # Shouldn't have negative numbers anyway...
      print("")
      summary.append((ff[0], ff[2], contribTotal, contribDiff, members, fractionNonZero, contribPerHourPerMemberNZ))
    lastFleetName = ff[0]
    lastFileTime = ff[2]
    lastContribTotal = contribTotal
    lastCharContrib = charContrib

print("\n===\n")

print("{0:<25}{1:<21}{2:<14}{3:<11}{4:<6}{5:<8}{6:<8}".format("Name", "Date", "Total", "Diff", "#", "% NZ",
                                                              "Per Hour Per Non-Zero Member"))
for s in summary:
  print("{0:25}{1:%Y-%m-%d %H:%M:%S}{2:13,}{3: 12,}{4:5d}{5: 8.2f}{6: 9.2f}".format(s[0], s[1], s[2], s[3], s[4],
                                                                                    100 * s[5],
                                                                                    int((100 * s[6] + 0.5)) / 100))






