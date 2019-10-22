from __future__ import print_function
import os
import copy
import math
import threading
import time

# Function List:
# 1. netRead: read the benchmark file and build circuit netlist
# 2. gateCalc: function that will work on the logic of each gate
# 3. inputRead: function that will update the circuit dictionary made in netRead to hold the line values
# 4. basic_sim: the actual simulation
# 5. main: The main function
# 6. counterGen: takes seed and creates a list s0,s1,s(n+1) till n = 255
# 7. lfsrGen: uses lfsrCalc to simulate a linear lfsr @ 2,3,4 and return an array[0-254]. Last one holds all strins combined
# 8. TVA_gen: Generates an array to be used to create TV_A
# 9. TVB_gen: Generates an array to be used to create TV_B
# 10. TVC_gen: Generates an array to be used to create TV_C
# 11. TVD_gen: Geneartes an array to be used to create TV_D
# 12. TVE_gen: Geneartes an array to be used to create TV_E

# FUNCTION:
def genFaultList(circuit):
    # Open a txt file to write our things on
    # If file doesn't exist, it will be made using the name given
    output = open("fault_list.txt", "w")

    # Creating a list to be returned to the main code
    allFaults = []

    # Go over all the inputs and...
    for x in circuit["INPUTS"][1]:
        # ... write input-SA-0/1 to ...
        toWrite = x[5:] + "-SA-"
        # ... the txt file,...
        output.write(toWrite + "0\n")
        output.write(toWrite + "1\n\n")
        # ... the list, and ...
        allFaults.append(toWrite + "0")
        allFaults.append(toWrite + "1")
        # ... onto the screen
        print(toWrite + "0\n" + toWrite + "1")

    # Go over all the gates and ...
    for x in circuit["GATES"][1]:
        # ... do the same thing to the gate outputs
        toWrite = x[5:] + "-SA-"
        output.write(toWrite + "0\n")
        output.write(toWrite + "1\n")
        allFaults.append(toWrite + "0")
        allFaults.append(toWrite + "1")
        print(toWrite + "0\n" + toWrite + "1")

        # ... Also, go over all of the gates' inputs and ...
        for y in circuit[x][1]:
            # do the same thing except name it OUTPUT-IN-INPUT-SA-0/1
            toWrite0 = x[5:] + "-IN-" + y[5:] + "-SA-"
            output.write(toWrite0 + "0\n")
            output.write(toWrite0 + "1\n")
            allFaults.append(toWrite0 + "0")
            allFaults.append(toWrite0 + "1")
            print(toWrite0 + "0\n" + toWrite0 + "1")
        output.write("\n")
    input("Press Enter To Continue...")
    return allFaults


# FUNCTION:
def readFaults(allFaults, faultFile):
    # Read the the given file
    inFault = open(faultFile, "r")

    # Create list of active faults
    activeFaults = []

    # For each line in the txt file, see if they're part of the available faults
    for x in inFault:
        # Initializing output variable each input line
        output = ""

        # Do nothing else if empty lines, ...
        if (x == "\n"):
            continue
        # ... or any comments
        if (x[0] == "#"):
            continue

        # Removing the the newlines at the end and then output it to the txt file
        x = x.replace("\n", "")

        # Removing spaces
        x = x.replace(" ", "")

        flag = False
        for y in allFaults:
            if x == y:
                flag = True
                break
        if flag:
            activeFaults.append([x, False])  # if they are, add them to the list
        else:
            print("ERROR: Fault can not exist in the circuit: " + x)  # Otherwise, tell the user
    return activeFaults


# FUNCTION:
def fault_sim(circuit, activeFaults, inputCircuit, goodOutput, faultFile):
    toOutput = []
    for x in activeFaults:
        output = ''
        circuit = copy.deepcopy(inputCircuit)

        xSplit = x[0].split("-SA-")

        # Get the value to which the node is stuck at
        value = xSplit[1]

        currentFault = "wire_" + xSplit[0]

        if "-IN-" not in currentFault:
            circuit[currentFault][3] = value
            circuit[currentFault][2] = True

        else:
            currentFault = currentFault.split("-IN-")
            circuit[currentFault[0]][1].remove("wire_" + currentFault[1])
            circuit[currentFault[0]][1].append(value)
        # print("x="+str(x))
        # printCkt(circuit)

        basic_sim(circuit)

        # print("AFTER:")
        # printCkt(circuit)
        for y in circuit["OUTPUTS"][1]:
            if not circuit[y][2]:
                output = "NETLIST ERROR: OUTPUT LINE \"" + y + "\" NOT ACCESSED"
                break
            output = str(circuit[y][3]) + output
        if output != goodOutput:
            x[1] = True
            toOutput.append(x[0] + " -> " + output)
    if len(toOutput) != 0:
        faultFile.write("detected:\n")
        print("detected:")
        for line in toOutput:
            print(line)
            faultFile.write('\t' + line + '\n')
        print("\n*******************\n")
        faultFile.write('\n')
    return activeFaults


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Neatly prints the Circuit Dictionary:
def printCkt(circuit):
    print("INPUT LIST:")
    for x in circuit["INPUTS"][1]:
        print(x + "= ", end='')
        print(circuit[x])

    print("\nOUTPUT LIST:")
    for x in circuit["OUTPUTS"][1]:
        print(x + "= ", end='')
        print(circuit[x])

    print("\nGATE list:")
    for x in circuit["GATES"][1]:
        print(x + "= ", end='')
        print(circuit[x])
    print()


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Reading in the Circuit gate-level netlist file:
def netRead(netName):
    # Opening the netlist file:
    netFile = open(netName, "r")

    # temporary variables
    inputs = []     # array of the input wires
    outputs = []    # array of the output wires
    gates = []      # array of the gate list
    inputBits = 0   # the number of inputs needed in this given circuit

    # main variable to hold the circuit netlist, this is a dictionary in Python, where:
    # key = wire name; value = a list of attributes of the wire
    circuit = {}

    #Fast processing SAM
    completed_queue = []
    leftovers_queue = []

    # Reading in the netlist file line by line
    for line in netFile:

        # NOT Reading any empty lines
        if (line == "\n"):
            continue

        # Removing spaces and newlines
        line = line.replace(" ", "")
        line = line.replace("\n", "")
        line = line.upper()

        # NOT Reading any comments
        if (line[0] == "#"):
            continue

        # @ Here it should just be in one of these formats:
        # INPUT(x)
        # OUTPUT(y)
        # z=LOGIC(a,b,c,...)

        # Read a INPUT wire and add to circuit:
        if (line[0:5] == "INPUT"):
            # Removing everything but the line variable name
            line = line.replace("INPUT", "")
            line = line.replace("(", "")
            line = line.replace(")", "")

            # Format the variable name to wire_*VAR_NAME*
            line = "wire_" + line

            # Error detection: line being made already exists
            if line in circuit:
                msg = "NETLIST ERROR: INPUT LINE \"" + line + "\" ALREADY EXISTS PREVIOUSLY IN NETLIST"
                print(msg + "\n")
                return msg

            completed_queue.append(line)

            # Appending to the inputs array and update the inputBits
            inputs.append(line)

            # add this wire as an entry to the circuit dictionary
            circuit[line] = ["INPUT", line, False, 'U']

            inputBits += 1
            print(line)
            print(circuit[line])
            continue

        # Read an OUTPUT wire and add to the output array list
        # Note that the same wire should also appear somewhere else as a GATE output
        if line[0:6] == "OUTPUT":
            # Removing everything but the numbers
            line = line.replace("OUTPUT", "")
            line = line.replace("(", "")
            line = line.replace(")", "")

            # Appending to the output array
            outputs.append("wire_" + line)
            continue

        # Read a gate output wire, and add to the circuit dictionary
        lineSpliced = line.split("=")  # splicing the line at the equals sign to get the gate output wire
        gateOut = "wire_" + lineSpliced[0]

        # Error detection: line being made already exists
        if gateOut in circuit:
            msg = "NETLIST ERROR: GATE OUTPUT LINE \"" + gateOut + "\" ALREADY EXISTS PREVIOUSLY IN NETLIST"
            print(msg + "\n")
            return msg

        lineSpliced = lineSpliced[1].split("(") # splicing the line again at the "("  to get the gate logic
        logic = lineSpliced[0].upper()

        lineSpliced[1] = lineSpliced[1].replace(")", "")
        terms = lineSpliced[1].split(",")  # Splicing the the line again at each comma to the get the gate terminals
        # Turning each term into an integer before putting it into the circuit dictionary
        terms = ["wire_" + x for x in terms]

            # add the gate output wire to the circuit dictionary with the dest as the key
        circuit[gateOut] = [logic, terms, False, 'U']

        #following check if all terms have been discovered
        temp_to_check_terms_available = len(terms)
        for t in terms:
            if t in completed_queue:
                temp_to_check_terms_available -= 1

        if temp_to_check_terms_available == 0:  # if 0 all terms have been discovered already
            # Appending the dest name to the gate list
            gates.append(gateOut)
            completed_queue.append(gateOut)
        else:
            leftovers_queue.append(gateOut)

    #Finish up the ordering SAM
    while len(leftovers_queue):
        currgate = leftovers_queue[0]
        terms = circuit[currgate][1]
        temp_to_check_terms_available = len(terms)
        for t in terms:
            if t in completed_queue:
                temp_to_check_terms_available -= 1
        if temp_to_check_terms_available == 0:
            gates.append(currgate)
            completed_queue.append(currgate)
            del leftovers_queue[0]
        else:
            leftovers_queue.append(currgate)
            del leftovers_queue[0]

    # now after each wire is built into the circuit dictionary,
    # add a few more non-wire items: input width, input array, output array, gate list
    # for convenience

    circuit["INPUT_WIDTH"] = ["input width:", inputBits]
    circuit["INPUTS"] = ["Input list", inputs]
    circuit["OUTPUTS"] = ["Output list", outputs]
    circuit["GATES"] = ["Gate list", gates]

    print("\n bookkeeping items in circuit: \n")
    print(circuit["INPUT_WIDTH"])
    print(circuit["INPUTS"])
    print(circuit["OUTPUTS"])
    print(circuit["GATES"])

    return circuit

# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: calculates the output value for each logic gate
def gateCalc(circuit, node):
    terminals = []

    # terminal will contain all the input wires of this logic gate (node)
    for gate in list(circuit[node][1]):

        if gate in ['0', '1', 'U']:
            terminals.append(gate)
        else:
            terminals.append(circuit[gate][3])

    # print(terminals)
    # terminals = list(circuit[node][1])
    # If the node is an Inverter gate output, solve and return the output
    if circuit[node][0] == "NOT":
        if terminals[0] == '0':
            circuit[node][3] = '1'
        elif terminals[0] == '1':
            circuit[node][3] = '0'
        elif terminals[0] == "U":
            circuit[node][3] = "U"
        else:  # Should not be able to come here
            return -1
        return circuit

    # If the node is an AND gate output, solve and return the output
    elif circuit[node][0] == "AND":
        # Initialize the output to 1
        circuit[node][3] = '1'
        # Initialize also a flag that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 0 at any input terminal, AND output is 0. If there is an unknown terminal, mark the flag
        # Otherwise, keep it at 1
        for term in terminals:
            if term == '0':
                circuit[node][3] = '0'
                break
            if term == "U":
                unknownTerm = True

        if unknownTerm:
            if circuit[node][3] == '1':
                circuit[node][3] = "U"
        return circuit

    # If the node is a NAND gate output, solve and return the output
    elif circuit[node][0] == "NAND":
        # Initialize the output to 0
        circuit[node][3] = '0'
        # Initialize also a variable that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 0 terminal, NAND changes the output to 1. If there is an unknown terminal, it
        # changes to "U" Otherwise, keep it at 0
        for term in terminals:
            if term == '0':
                circuit[node][3] = '1'
                break
            if term == "U":
                unknownTerm = True
                break

        if unknownTerm:
            if circuit[node][3] == '0':
                circuit[node][3] = "U"
        return circuit

    # If the node is an OR gate output, solve and return the output
    elif circuit[node][0] == "OR":
        # Initialize the output to 0
        circuit[node][3] = '0'
        # Initialize also a variable that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 1 terminal, OR changes the output to 1. Otherwise, keep it at 0
        for term in terminals:
            if term == '1':
                circuit[node][3] = '1'
                break
            if term == "U":
                unknownTerm = True

        if unknownTerm:
            if circuit[node][3] == '0':
                circuit[node][3] = "U"
        return circuit

    # If the node is an NOR gate output, solve and return the output
    if circuit[node][0] == "NOR":
        # Initialize the output to 1
        circuit[node][3] = '1'
        # Initialize also a variable that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 1 terminal, NOR changes the output to 0. Otherwise, keep it at 1
        for term in terminals:
            if term == '1':
                circuit[node][3] = '0'
                break
            if term == "U":
                unknownTerm = True
        if unknownTerm:
            if circuit[node][3] == '1':
                circuit[node][3] = "U"
        return circuit

    # If the node is an XOR gate output, solve and return the output
    if circuit[node][0] == "XOR":
        # Initialize a variable to zero, to count how many 1's in the terms
        count = 0

        # if there are an odd number of terminals, XOR outputs 1. Otherwise, it should output 0
        for term in terminals:
            if term == '1':
                count += 1  # For each 1 bit, add one count
            if term == "U":
                circuit[node][3] = "U"
                return circuit

        # check how many 1's we counted
        if count % 2 == 1:  # if more than one 1, we know it's going to be 0.
            circuit[node][3] = '1'
        else:  # Otherwise, the output is equal to how many 1's there are
            circuit[node][3] = '0'
        return circuit

    # If the node is an XNOR gate output, solve and return the output
    elif circuit[node][0] == "XNOR":
        # Initialize a variable to zero, to count how many 1's in the terms
        count = 0

        # if there is a single 1 terminal, XNOR outputs 0. Otherwise, it outputs 1
        for term in terminals:
            if term == '1':
                count += 1  # For each 1 bit, add one count
            if term == "U":
                circuit[node][3] = "U"
                return circuit

        # check how many 1's we counted
        if count % 2 == 1:  # if more than one 1, we know it's going to be 0.
            circuit[node][3] = '0'
        else:  # Otherwise, the output is equal to how many 1's there are
            circuit[node][3] = '1'
        return circuit

    # Error detection... should not be able to get at this point
    return circuit[node][0]

#LFSR acutal
def linearCalc(initalVal):
    temp = initalVal[0] #Get the MSB
    sBinary = initalVal[-7:]

    xorVals = int(sBinary[3:6]) ^ int(temp+temp+temp)
    sBinary = sBinary[0:3] + repr(xorVals).zfill(3) + sBinary[6:7] + temp #final value
    return sBinary
 
#LSFR looper
#seed has to be before 255
def lfsrGen(seed):
    lfsrSeq, lfsrSeqBin = "", []
    initalVal = bin(seed)[2:].zfill(8)

    lfsrSeq = initalVal + lfsrSeq
    lfsrSeqBin.append(initalVal)

    currentVal = linearCalc(initalVal)
    while initalVal != currentVal:
        lfsrSeq = currentVal + lfsrSeq #save 
        lfsrSeqBin.append(currentVal)

        currentVal = linearCalc(currentVal)

    lfsrSeqBin.append(lfsrSeq)
    print(lfsrSeqBin)
    return lfsrSeqBin

# LFSR acutal
def linearCalc(initalVal):
    temp = initalVal[0]  # Get the MSB
    sBinary = initalVal[-7:]

    xorVals = int(sBinary[3:6]) ^ int(temp + temp + temp)
    sBinary = sBinary[0:3] + repr(xorVals).zfill(3) + sBinary[6:7] + temp  # final value
    return sBinary

# Basic counter for TV A ~ C
def counterGen(seed):
    counterBin = []
    initialVal = int(seed)
    for x in range(0, 255):
        counterBin.append(initialVal)
        initialVal += 1

    print(counterBin)
    return counterBin
# LFSR looper
# seed has to be before 255
def lfsrGen(seed):
    lfsrSeq, lfsrSeqBin = "", []
    initalVal = bin(seed)[2:].zfill(8)
    lfsrSeq = initalVal + lfsrSeq
    lfsrSeqBin.append(initalVal)

    currentVal = linearCalc(initalVal)
    while initalVal != currentVal:
        lfsrSeq = currentVal + lfsrSeq  # save
        lfsrSeqBin.append(currentVal)

        currentVal = linearCalc(currentVal)

    lfsrSeqBin.append(lfsrSeq)
    print(lfsrSeqBin)
    return lfsrSeqBin


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Updating the circuit dictionary with the input line, and also resetting the gates and output lines
def inputRead(circuit, line):
    # Checking if input bits are enough for the circuit
    if len(line) < circuit["INPUT_WIDTH"][1]:
        return -1

    # Getting the proper number of bits:
    line = line[(len(line) - circuit["INPUT_WIDTH"][1]):(len(line))]

    # Adding the inputs to the dictionary
    # Since the for loop will start at the most significant bit, we start at input width N
    i = circuit["INPUT_WIDTH"][1] - 1
    inputs = list(circuit["INPUTS"][1])
    # dictionary item: [(bool) If accessed, (int) the value of each line, (int) layer number, (str) origin of U value]
    for bitVal in line:
        bitVal = bitVal.upper()  # in the case user input lower-case u
        circuit[inputs[i]][3] = bitVal  # put the bit value as the line value
        circuit[inputs[i]][2] = True  # and make it so that this line is accessed

        # In case the input has an invalid character (i.e. not "0", "1" or "U"), return an error flag
        if bitVal != "0" and bitVal != "1" and bitVal != "U":
            return -2
        i -= 1  # continuing the increments

    return circuit


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: the actual simulation #
def basic_sim(circuit):
    # QUEUE and DEQUEUE
    # Creating a queue, using a list, containing all of the gates in the circuit
    queue = list(circuit["GATES"][1])
    i = 1

    while True:
        i -= 1
        # If there's no more things in queue, done
        if len(queue) == 0:
            break

        # Remove the first element of the queue and assign it to a variable for us to use
        curr = queue[0]
        queue.remove(curr)

        if circuit[curr][2]:
            continue

        # initialize a flag, used to check if every terminal has been accessed
        term_has_value = True

        # Check if the terminals have been accessed
        for term in circuit[curr][1]:
            if term in ['1', '0', 'U']:
                continue
            elif not circuit[term][2]:
                term_has_value = False
                break

        if term_has_value:
            circuit[curr][2] = True
            circuit = gateCalc(circuit, curr)

            # ERROR Detection if LOGIC does not exist
            if isinstance(circuit, str):
                print(circuit)
                return circuit

            # print("Progress: updating " + curr + " = " + circuit[curr][3] + " as the output of " + circuit[curr][0] + " for:")
            # for term in circuit[curr][1]:
            #    if term in ['1','0','U']:
            #        print(term + " = "+ term)
            #    else:
            #        print(term + " = " + circuit[term][3])
            #
            # print("\nPress Enter to Continue...")
            # input()

        else:
            # If the terminals have not been accessed yet, append the current node at the end of the queue
            queue.append(curr)

    return circuit

# one N-Bit counter [0,0,0,0,80] in binary fills bits 0 ~ 24 with 0s
# returns list for TV_A generation
def TVA_gen(counterBin):
    TVA_list = []
    for x in range(0, 255):
        currVal = counterBin[x]
        binVal = bin(currVal)[2:].zfill(36)
        TVA_list.append(binVal + "\n")
    return TVA_list

#multi 8-bit counter [80,80,80,80,80] in binary
# returns list for TV_B generation
def TVB_gen(counterBin):
    TVB_list = []
    for x in range(0, 255):
        currVal = counterBin[x]
        binVal = bin(currVal)[2:].zfill(8)
        finalVal = str(binVal)*5
        finalVal = finalVal[4:40]
        TVB_list.append(finalVal + "\n")
    return TVB_list

# +1 counter multi 8-bit "diff seed" [84,83,82,81,80], [85,84,83,82,81], etc in binary
# returns list for TV_C generation
def TVC_gen(counterBin):
    TVC_list = []
    for x in range(0, 255):
        tempBin = ""
        currVal = counterBin[x]
        for y in range(0, 5):
            tempVal = str(bin(currVal)[2:].zfill(8))
            tempBin = tempVal + tempBin
            print(tempBin)
            currVal += 1
        TVC_list.append(tempBin[4:40] + "\n")
    return TVC_list

# takes inputsize of the circuit, And the global variable that hold LFSR sequence
# returns list for TV_D geneartion
def TVD_gen(inSize, lfsrSeqBin):
    TVD_list = []
    for x in range(0, 255):
        inputSize = inSize
        currVal = lfsrSeqBin[x] #curr s0->s1->s2
        leftoverSize = inputSize % 8
        inputSize = int((inputSize - leftoverSize)/8)
        TVD_list.append(currVal[-1*leftoverSize:] + (currVal*inputSize) + "\n")
    return TVD_list

#takes inputsize of the circuit, And the global variable that hold LFSR sequence
#returns list for TV_E geneartion
def TVE_gen(inputSize, lfsrSeq):
    TVE_list = []
    start, end = len(lfsrSeq)-inputSize, len(lfsrSeq)
    for x in range(0, 255):
        if(start < 0):
            start = 2040 + start
        if(end < 0):
            end = 2040 + end
        if(start < end):
            TVE_list.append(lfsrSeq[start:end] + "\n")
        elif(start > end):
            TVE_list.append(lfsrSeq[start:] + lfsrSeq[0:end] + "\n")
        start -= 8
        end -= 8
    return TVE_list

# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Main Function
def main():
    # **************************************************************************************************************** #
    # NOTE: UI code; Does not contain anything about the actual simulation

    # Used for file access
    script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in
    genOnly = False
    cktOnly = False
    print("Circuit Simulator:")

    while True:
        print("\n Pick a selection:")
        print(" (1) Fault generator")
        print(" (2) Circuit Simulator")
        print(" (3) Fault Simulator")
        userInput = input("\n Select from 1-3: ")
        if userInput == "1":
            genOnly = True
            break
        elif userInput == "2":
            cktOnly = True
            break
        elif userInput == '3':
            break

    # Select circuit benchmark file, default is circuit.bench
    while True:
        cktFile = "circuit.bench"
        print("\n Read circuit benchmark file: use " + cktFile + "?" + " Enter to accept or type filename: ")
        userInput = input()
        if userInput == "":
            break
        else:
            cktFile = os.path.join(script_dir, userInput)
            if not os.path.isfile(cktFile):
                print("File does not exist. \n")
            else:
                break

    print("\n Reading " + cktFile + " ... \n")
    circuit = netRead(cktFile)
    print("\n Finished processing benchmark file and built netlist dictionary: \n")
    # printCkt(circuit)

    # project 2
    while True:
        seed = input("What is your seed value in integer: ")
        if seed.isdigit():
            seed = int(seed)
            if ((seed < 255) and (seed > 0)):
                break

    while True:
        batchSize = input("Choose a batch size in [1, 10]: ")
        if batchSize.isdigit():
            batchSize = int(batchSize)
            if ((batchSize < 255) and (batchSize > 0)):
                break

    counterBin = counterGen(seed)
    lfsrSeqBin = lfsrGen(seed)  # creates lfsr based on the seed
    inputSize = circuit["INPUT_WIDTH"][1]  # hold the number of inputs

    # creates the TV_A.txt
    TVA_Output = open(os.path.join(script_dir, "TV_A.txt"), "w")
    for a in TVA_gen(counterBin):
        TVA_Output.write(a)
    TVA_Output.close()

    TVB_Output = open(os.path.join(script_dir, "TV_B.txt"), "w")
    for b in TVB_gen(counterBin):
        TVB_Output.write(b)
    TVB_Output.close()

    TVC_Output = open(os.path.join(script_dir, "TV_C.txt"), "w")
    for c in TVC_gen(counterBin):
        TVC_Output.write(c)
    TVC_Output.close()

    # creates the TV_D.txt
    TVD_Output = open(os.path.join(script_dir, "TV_D.txt"), "w")
    for d in TVD_gen(inputSize, lfsrSeqBin):
        TVD_Output.write(d)
    TVD_Output.close()

    # creates the TV_E.txt
    TVE_Output = open(os.path.join(script_dir, "TV_E.txt"), "w")
    for e in TVE_gen(inputSize, lfsrSeqBin[255]):
        TVE_Output.write(e)
    TVE_Output.close()

    # Make header for the csv file
    csvFile = open(os.path.join(script_dir, "f_avg.csv"), "w")
    csvFile.write("Batch #, A, B, C, D, E, seed = " + repr(seed) + ", Batch size = " + repr(batchSize))
    # start_time = time.time()
    # print("--- %s seconds ---" % (time.time() - start_time))





    #project 2
    while True:
        seed = input("What is your seed value in integer: ")
        if seed.isdigit():
            seed = int(seed)
            if ((seed < 255) and (seed > 0)): 
                break

    while True:
        batchSize = input("Choose a batch size in [1, 10]: ")
        if batchSize.isdigit():
            batchSize = int(batchSize)
            if ((batchSize < 255) and (batchSize > 0)): 
                break

    lfsrSeqBin = lfsrGen(seed) #creates lfsr based on the seed
    inputSize = circuit["INPUT_WIDTH"][1] #hold the number of inputs

    #creates the TV_D.txt       
    TVD_Output = open(os.path.join(script_dir, "TV_D.txt"), "w")
    for d in TVD_gen(inputSize, lfsrSeqBin):
        TVD_Output.write(d)
    TVD_Output.close()

    #creates the TV_E.txt
    TVE_Output = open(os.path.join(script_dir, "TV_E.txt"), "w")
    for e in TVE_gen(inputSize, lfsrSeqBin[255]):
        TVE_Output.write(e)
    TVE_Output.close() 


    #Make header for the csv file
    csvFile = open(os.path.join(script_dir, "f_avg.csv"), "w")
    csvFile.write("Batch #, A, B, C, D, E, seed = " + repr(seed) + ", Batch size = " + repr(batchSize))
    #start_time = time.time()
    #print("--- %s seconds ---" % (time.time() - start_time))




    if not cktOnly:
        allFaults = genFaultList(circuit)
        if genOnly:
            exit()
        faultFile = "f_list.txt"
        activeFaults = readFaults(allFaults, faultFile)
        if len(activeFaults) < 1:
            print("ERROR: No compatible faults found in f_list.txt")
            exit()
    # keep an initial (unassigned any value) copy of the circuit for an easy reset
    newCircuit = copy.deepcopy(circuit)

    # Select input file, default is input.txt
    while True:
        inputName = "input.txt"
        print("\n Read input vector file: use " + inputName + "?" + " Enter to accept or type filename: ")
        userInput = input()
        if userInput == "":

            break
        else:
            inputName = os.path.join(script_dir, userInput)
            if not os.path.isfile(inputName):
                print("File does not exist. \n")
            else:
                break

    # Select output file, default is output.txt
    while True:
        outputName = "output.txt"
        print("\n Write output file: use " + outputName + "?" + " Enter to accept or type filename: ")
        userInput = input()
        if userInput == "":
            break
        else:
            outputName = os.path.join(script_dir, userInput)
            break

    # Note: UI code;
    # **************************************************************************************************************** #

    print("\n *** Simulating the" + inputName + " file and will output in" + outputName + "*** \n")
    inputFile = open(inputName, "r")
    outputFile = open(outputName, "w")



    if not cktOnly:
        faultFile = open("fault_sim_result.txt", "w")

    # Runs the simulator for each line of the input file
    for line in inputFile:
        # Initializing output variable each input line
        output = ""

        # Do nothing else if empty lines, ...
        if (line == "\n"):
            continue
        # ... or any comments
        if (line[0] == "#"):
            continue

        # Removing the the newlines at the end and then output it to the txt file
        line = line.replace("\n", "")
        outputFile.write(line)
        if not cktOnly:
            faultFile.write(line)
        # Removing spaces
        line = line.replace(" ", "")

        print("\n ---> Now ready to simulate INPUT = " + line)
        circuit = inputRead(circuit, line)

        if circuit == -1 or circuit == -2:
            print("INPUT ERROR: INSUFFICIENT BITS")
            print("INPUT ERROR: INVALID INPUT VALUE/S")
            # After each input line is finished, reset the netList
            circuit = newCircuit
            continue

        # printCkt(circuit)
        inputCircuit = copy.deepcopy(circuit)
        circuit = basic_sim(circuit)
        print("\n *** Finished simulation - resulting circuit: \n")
        # printCkt(circuit)

        for y in circuit["OUTPUTS"][1]:
            if not circuit[y][2]:
                output = "NETLIST ERROR: OUTPUT LINE \"" + y + "\" NOT ACCESSED"
                break
            output = str(circuit[y][3]) + output

        print("\n *** Summary of simulation: ")
        print(line + " -> " + output + " written into output file. \n")
        outputFile.write(" -> " + output + "\n")
        if not cktOnly:
            faultFile.write(" -> " + output + "\n")
        # Now, work on each given fault
        if not cktOnly:
            activeFaults = fault_sim(circuit, activeFaults, inputCircuit, output, faultFile)

        input("Press Enter to Continue...")

        # After each input line is finished, reset the circuit
        print("\n *** Now resetting circuit back to unknowns... \n")

        circuit = copy.deepcopy(newCircuit)

        # print("\n circuit after resetting: \n")
        # printCkt(circuit)
        print("\n*******************\n")

    if not cktOnly:
        i = 0.0
        for x in activeFaults:
            if x[1]:
                i += 1    
        print("fault coverage:" + str(i) + "/" + str(len(activeFaults)) +"="+str(round(100.0*float(i)/float(len(activeFaults)),2))+"%")
        faultFile.write("fault coverage:" + str(i) + "/" + str(len(activeFaults)) +"="+str(round(100.0*float(i)/float(len(activeFaults)),2))+"%")
    
        faultFile.close()
    outputFile.close()
    csvFile.close()
    #exit()


if __name__ == "__main__":
    main()
