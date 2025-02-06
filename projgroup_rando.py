from random import randint, shuffle
import csv
import sys
import argparse
import yaml
from pathlib import Path
from os import rename


def main():
    parser = argparse.ArgumentParser(description='Generate project groups from a CSV file.')
    parser.add_argument('csv_file_path', type=str, help='Path to the CSV file')
    parser.add_argument('--generate', action='store_true', help='Generate a CSV file of project group pairs for peer review')
    parser.add_argument('--rename', nargs='?', type=str, action='store', help='Convert Gradescope submission filenames to the appropriate target group using metadata YAML file and a generated groups csv. Pass YAML file path.')
    args = parser.parse_args()

    if args.generate:
        generate_groups(args.csv_file_path)
    elif args.rename:
        process_gradescope(args.csv_file_path, args.rename)



def generate_groups(csv_file):
    
    csv_file_path = sys.argv[1]
    csv_file = open(csv_file_path, 'r')
    
    
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
    print("Finished generating group pairs.")
    
    print("Writing to CSV file...")
    write_csv(project_groups, group_info)



def write_csv(project_groups, group_info):    
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
            
            for i in enumerate(tup):
                output['Project'] = 'Project ' + str(pnum)
                output['Group A'] = tup[i][0]
                output['Group B'] = tup[i][1]
                output['Group A Email'] = group_info[tup[i][0]]['emails']
                output['Group B Email'] = group_info[tup[i][1]]['emails']
                output['Group A Names'] = group_info[tup[i][0]]['names']
                output['Group B Names'] = group_info[tup[i][1]]['names']
                writer.writerow(output)
            pnum += 1
        
    print("Written to CSV file projgroups.csv")


def process_gradescope(csv_path, yaml_path):
    yml_file = open(yaml_path, 'r')
    csv_file = open(csv_path, 'r')
    with open('eval_sources.txt', 'w') as f:
        f.write("Sources of eval by filename:\n")
    
    cread = csv.DictReader(csv_file)
    pairinfo = []
    for row in cread:
        pairinfo.append(row)
    ymlread = yaml.load_all(yml_file, Loader=yaml.FullLoader)
    metadata = {}
    
    filedir = Path(yaml_path).parent
    # print(filedir)
    for y in ymlread:
        for file, data in y.items():
            orig = Path(filedir).joinpath(file)
            target = None
            found = False
            for i in range(0, len(data[':submitters'])):
                
                if found:
                    break
                name = data[':submitters'][i][':name']
                
                
                for d in pairinfo:
                    # print(d['Project'])
                    if d['Project'] == 'Project 1': ## Have to set this manually for now
                        if name in d['Group A Names']:
                            target = d['Group B']
                            # print(target + '>>>' + d['Group A'])
                            # print(str(orig))
                            rename_file(orig, target, d['Group A'])
                            found = True
                        elif name in d['Group B Names']:
                            target = d['Group A']
                            # print(target + '>>>' + d['Group B'])
                            # print(str(orig))
                            rename_file(orig, target, d['Group B'])
                            found = True
            # print("Could not match name for " + name + " in " + str(orig))
    

def rename_file(orig, target, src):
    stem = orig.stem
    target = target.replace(" ", "_")
    newname = str(orig).replace(stem, "P1PeerEval_sendto_" + target)
    
    with open('eval_sources.txt', 'a') as f:
        f.write(str(orig) + " -> " + newname + " (from " + src + ")\n")
    print(newname)
    print(orig)
    
    rename(orig, newname)
    print("Renamed " + str(orig) + " to " + newname)



if __name__ == "__main__":
    main()