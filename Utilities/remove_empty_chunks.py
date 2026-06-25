import os
import csv

def is_all_zero(csv_file):

    with open(csv_file, newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            for cell in row:
                if cell.strip() != "0":
                    return False

    return True


removed = 0

for file in os.listdir("."):

    if file.lower().endswith(".csv"):

        if is_all_zero(file):
            os.remove(file)
            print("removed:", file)
            removed += 1


print("done")
print("chunks removed:", removed)