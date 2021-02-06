import random
import json


class Queue:
    def __init__(self):
        self.queue  = list()

    def isEmpty(self):
        return self.queue == []

    def enqueue(self, data):
        if data not in self.queue:
            self.queue.insert(0,data)

    def dequeue(self):
        if len(self.queue)>0:
            return self.queue.pop()

    def size(self):
        return len(self.queue)


def randomize(arr):
    n = len(arr)
    for i in range(n - 1, 0, -1):
        # Pick a random index from 0 to i
        j = random.randint(0, i)

        # Swap arr[i] with the element at random index
        arr[i], arr[j] = arr[j], arr[i]
    return arr


def createTimeTableJson(teacherRoaster, number_of_periods, number_of_standards):
    newRoaster ={}
    newRoaster.clear()
    availableTeachers = Queue()
    number_of_teachers = teacherRoaster.keys()

    number_of_teachers = randomize(number_of_teachers)
    teacherList = []

    for teacher in number_of_teachers:
        availableTeachers.enqueue((teacher, teacherRoaster[teacher][0]))

    for timeslot in range(1, number_of_periods + 1):
        for class_index in range(1, number_of_standards + 1):
            current_pair = availableTeachers.dequeue()
            current_ID = current_pair[0]
            teacherList.append(current_ID)
            current_details = current_pair[1]


            class_list = json.loads(current_details["classes"])

            availableTeachers.enqueue(current_pair)
            if class_index in class_list:
                current_details["Class Timings Today"].append(timeslot)
                current_details["Class Taken"].append(class_index)
            current_pair = (current_ID, current_details)
            availableTeachers.enqueue(current_pair)

    for item in availableTeachers.queue:
        newRoaster[item[0]] = item[1]

    for k, v in newRoaster.iteritems():
        index_list = []
        for index in range(1, 8):
            if index not in newRoaster[k]["Class Timings Today"]:
                index_list.append(index)
        for index in index_list:
            newRoaster[k]["Class Taken"].insert(index, "Free")

    return newRoaster
