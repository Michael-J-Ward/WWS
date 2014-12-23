

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time
import string
import pickle
import sys

SLOT_CATEGORY_ID = {'QB':   '0',
                    'RB':   '2',
                    'WR':   '4',
                    'TE':   '6',
                    'D/ST': '16',
                    'K':    '17'}

class ESPNDriver(object):
    def __init__(self, team):
        self.team = team
        self.driver = webdriver.Firefox()

    def generateURL(self, slotCategoryId=None):
        baseURL = 'http://games.espn.go.com/ffl/freeagency?'
        if slotCategoryId:
            return "{}leagueId={}&slotCategoryId={}".format(baseURL,self.team.getLeagueId(),slotCategoryId)
        else:
            return baseURL + "leagueId=" + self.team.getLeagueId()

    def parsePlayer(self,player):
        id_ = player.get_attribute('id')
        info = player.text.split()[:4] #only interested in the first 4 elements
        if info[1] == r'D/ST':  # then it's a defense
            name = info[0]
            position = info[1]
            return Player(id_, name, position, name, position)
        else:
            firstName = info[0]
            lastName = info[1].strip(string.punctuation) #extra comma and astericks can show up here
            team = info[2]
            position = info[3]
            return Player(id_, firstName, lastName, team, position)

    def login(self):
        driver = self.driver
        url = self.generateURL()
        driver.get(url)
        elem = driver.find_element_by_id('personalizationLink')
        elem.click()
        time.sleep(5)
        driver.switch_to.frame(driver.find_element_by_tag_name("iframe"))
        user = driver.find_element_by_id('username')
        user.send_keys(self.team.getUsername())
        passw = driver.find_element_by_id('password')
        passw.send_keys(self.team.getPassword())
        passw.send_keys(Keys.RETURN)

    def readRoster(self):
        self.login()
        time.sleep(5)
        driver = self.driver
        teamLink = driver.find_element_by_link_text("My Team")
        teamLink.click()
        time.sleep(5)
        roster = []
        players = driver.find_elements_by_class_name("playertablePlayerName")
        
        for player in players:
                tmp = self.parsePlayer(player)
                roster.append(tmp)

        self.team.updateRoster(roster)

    def playerSearch(self,lastName,slotCategoryId):
        url = self.generateURL(slotCategoryId)
        driver = self.driver
        driver.get(url)
        nameSearch = driver.find_element_by_id('lastNameInput')
        nameSearch.send_keys(lastName)
        nameSearch.send_keys(Keys.RETURN)
        time.sleep(5)

    def findAddPlayer(self, lastName, slotCategoryId):
        self.playerSearch(lastName,slotCategoryId)
        driver = self.driver
        players = driver.find_elements_by_class_name("playertablePlayerName")
        potentials = []
        for player in players:
            tmp = self.parsePlayer(player)
            potentials.append(tmp)

        i = 0
        for p in potentials:
            print i, p
            i+=1

        prompt = 'Enter the number of the player or leave blank to restart search\n'
        selection = raw_input(prompt)
        
        if len(selection) > 0:
            self.team.addTarget(potentials[int(selection)])
        else:
            startTargetSearch(self.team,self)

    def execTarget(self, target):
        slotCategoryId = SLOT_CATEGORY_ID[target.getPosition()]
        self.playerSearch(target.getLastName(), slotCategoryId)
        driver = self.driver
        try:
            player = driver.find_element_by_id(target.getID())
            addButton = player.find_element_by_class_name("addButton")
            addButton.click()
        except NoSuchElementException:
            target = self.team.getTargetList().pop(0)
            self.execTarget(target)



    def execDrop(self, dropTarget):
        driver = self.driver
        try:
            playerToDrop = driver.find_element_by_id(dropTarget.getID())
            dropBox = playerToDrop.find_element_by_class_name('select')
            dropBox.click()
            submitButton = driver.find_element_by_name('btnSubmit')
            submitButton.click()
            confirmButton = driver.find_element_by_name('confirmBtn')
            confirmButton.click()

    def execTransactions(self):
        self.login()
        driver = self.driver
        targets = self.team.getTargetList()
        drops = self.team.getDropList()
        while targets and drops:
            target = targets.pop(0)
            self.execTarget(target)

            dropTarget = drops.pop(0)
            self.execDrop(dropTarget)
        
        self.driver.close() 
                   
class Player(object):
    def __init__(self, player_id, firstName, lastName, team, position):
        self.id = self.parseID(player_id)
        self.firstName = firstName
        self.lastName = lastName
        self.team = team
        self.position = position

    def parseID(self, player_id):
        return 'plyr' + player_id.split('_')[1]

    def getID(self):
        return self.id

    def getLastName(self):
        return self.lastName

    def getPosition(self):
        return self.position

    def __str__(self):
        return "{} {}, {}, {}".format(self.firstName, self.lastName, self.position, self.team)

class Team(object):
    def __init__(self,username,password,leagueId,teamName=None):
        self.username = username
        self.password = password
        self.leagueId = leagueId
        self.teamName = teamName
        self.roster = []
        self.targets = []
        self.drops = []

    def getUsername(self):
        return self.username

    def getPassword(self):
        return self.password

    def getLeagueId(self):
        return self.leagueId

    def getTargetList(self):
        return self.targets

    def getDropList(self):
        return self.drops

    def getRoster(self):
        return self.roster

    def updateRoster(self, roster):
        self.roster = roster

    def addTarget(self, player):
        self.targets.append(player)

    def addDrop(self,player):
        self.drops.append(player)

    def clearTargets(self):
        self.targets = []

    def clearDrops(self):
        self.drops = []


def startTargetSearch(team,driver):
    lastName = raw_input("Enter Player's Last Name:\n")
    slotCategoryId = raw_input("Enter Player's slotCategoryId:\n")
    driver.findAddPlayer(lastName,slotCategoryId)

def dropSelection(team,driver):
    print "Potential Players to Drop\n"
    potentials = team.getRoster()
    i = 0

    for p in potentials:
        print i, p
        i+=1

    prompt = 'Enter the number of the player or leave blank to restart search\n'
    selection = raw_input(prompt)

    if len(selection) > 0:
        team.addDrop(potentials[int(selection)])
    else:
        dropSelection()

def actionSelection(team,driver):
    prompt = "Would you like to add another target? Y or N\n"
    ans = raw_input(prompt)
    if ans == 'Y':
        startTargetSearch(team,driver)
        actionSelection(team,driver)
        return
    prompt = "Would you like to add a drop player? Y or N\n"
    ans = raw_input(prompt)
    if ans == 'Y':
        dropSelection(team,driver)
        actionSelection(team,driver)
        return
    prompt = "Would you like to start over? Y or N\n"
    ans = raw_input(prompt)
    if ans == 'Y':
        team.clearDrops()
        team.clearTargets()
        actionSelection(team,driver)
        return
    prompt = "Would you like to save? Y or N\n"
    ans = raw_input(prompt)
    if ans == 'Y':
        saveData(team)
        return
    prompt = 'Would you like to see these options again? Y or N\n'
    ans = raw_input(prompt)
    if ans == 'Y':
        actionSelection(team,driver)
        return

def saveData(team):
    with open('team_data.pkl','wb') as output:
        pickle.dump(team,output,pickle.HIGHEST_PROTOCOL)

def main():
    username = raw_input("Please enter ESPN Username:\t")
    password = raw_input("Please enter ESPN Password:\t")
    leagueId = raw_input("Please enter ESPN League ID:\t")

    team = Team(username,password,leagueId)
    driver = ESPNDriver(team)
    driver.readRoster()
    actionSelection(team,driver)

def makeTransactions():
    with open('team_data.pkl','rb') as input:
        team = pickle.load(input)

    driver = ESPNDriver(team)
    driver.execTransactions()

if __name__=="__main__":
    if len(sys.argv) == 1:
        main()
    elif sys.argv[1] == 'makeTransactions':
        makeTransactions()
    else:
        pass