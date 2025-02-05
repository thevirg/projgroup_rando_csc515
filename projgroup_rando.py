from random import randint, shuffle
import csv
import sys

if len(sys.argv) < 2:
    print("Usage: python projgroup_rando.py <csv_file_path>")
    sys.exit(1)

csv_file_path = sys.argv[1]
csv_file = open(csv_file_path, 'r')

# csv_file = open(,, 'r')

reader = csv.reader(csv_file)
k = 0
g = 0

groups = {    
    "group 1": 1,
    "group 2": 1,
    "group 3": 1,
    "group 4": 1,
    "group 5": 1,
    "group 6": 1,
    "group 7": 1,
    "group 8": 1,
    "group 9": 1,
    "group 10": 1,
    "group 11": 1,
    "group 12": 1,
    "group 13": 1,
    "group 14": 1,
    "group 15": 1,
    "group 16": 1,
    "group 17": 1,
    "group 18": 1
}

# print(groups.keys())
next(reader, None)
group_info = {
    "group 1": 1,
    "group 2": 1,
    "group 3": 1,
    "group 4": 1,
    "group 5": 1,
    "group 6": 1,
    "group 7": 1,
    "group 8": 1,
    "group 9": 1,
    "group 10": 1,
    "group 11": 1,
    "group 12": 1,
    "group 13": 1,
    "group 14": 1,
    "group 15": 1,
    "group 16": 1,
    "group 17": 1,
    "group 18": 1
}
for row in reader:
    tmpgrp = {
        'names': [],
        'emails': []
    }
    for k in range(0, len(row), 2):
        tmpgrp['names'].append(str(row[k]) + ", ")
        tmpgrp['emails'].append(str(row[k+1]) + ", ")
    
    group_info['group ' + str(g+1)] = tmpgrp
    g += 1
        

# n = [10,11,12,13,14,15,16,17,18]
tupleHash = []

project_groups = [[],[],[],[]]


for i in range(0,4):
    n = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18]
    for k in groups.keys():
        # print(k)
        current = int(str(k)[-2:])
        shuffle(n)
        found = False
        if current not in n:
            continue
        while not found:
            num = n.pop()
            tmp = (k, "group " + str(num))
            if hash(tmp) in tupleHash or tmp[0] == tmp[1]:
                n.append(num)
                shuffle(n)
                continue    
            tupleHash.append(hash(tmp))
            project_groups[i-1].append(tmp)
            found = True
            # print(tmp)
            # print(str(k))
            # print(str(k)[-2:])
            if current in n:
                n.remove(current)
        
output = {}
    
    
with open('projgroups.csv', 'w') as csvfile:
    fieldnames = ['Project', 'Group A', 'Group B', 'Group A Email', 'Group B Email', 'Group A Names', 'Group B Names']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    pnum = 1
    for tup in project_groups:
        # print(tup)
        # print(tup[1])
        # print(tup[1][0])
        # print('\n')
        
        for i in range(0, len(tup)):
            output['Project'] = 'Project ' + str(pnum)
            output['Group A'] = tup[i][0]
            output['Group B'] = tup[i][1]
            output['Group A Email'] = group_info[tup[i][0]]['emails']
            output['Group B Email'] = group_info[tup[i][1]]['emails']
            output['Group A Names'] = group_info[tup[i][0]]['names']
            output['Group B Names'] = group_info[tup[i][1]]['names']
            writer.writerow(output)
        pnum += 1
    
print("done")