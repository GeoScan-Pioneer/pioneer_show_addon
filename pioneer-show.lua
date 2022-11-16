local unpack = table.unpack
local ledNumber = 5
local leds = Ledbar.new(ledNumber)

local state = {
    idle = 0,
    start = 1,
    takeoff = 2,
    flight = 3,
    landing = 4,
    inCheck = 5
}

local periodColors = 1 / NandLua.readFreqColors()
local numColors = NandLua.readNumberColors()
local periodPositions = 1 / NandLua.readFreqPositions()
local numPositions = NandLua.readNumberPositions()
local idPoint = 0
local idColor = 0
local onPosition = false
local GNSSReady = false
local isMotorStarted = false
local navSystem = getNavSystem()
local selfState = state.idle
local syncTime = 0

local function changeColor(col)
    for i = 0, ledNumber - 1, 1 do
        leds:set(i, unpack(col))
    end
end

local function getNearestTime(sec)
    if navSystem == 0 then
        return 18 + sec * (math.floor((time() + deltaTime() - 18) / sec) + 1)
    elseif navSystem == 1 then
        return sec * (math.floor((time() + deltaTime()) / sec) + 1)
    end
end

local function getGNSSState()
    if selfState == state.idle then
        selfState = state.inCheck
        local gnssStatus, gnssRtk, satTotal = Sensors.gnssInfo()
        if satTotal == 0 then
            changeColor({ 1, 0, 0 }) -- red
        elseif satTotal < 11 then
            changeColor({ 1, 1, 0 }) -- yellow
        elseif gnssRtk == 0 then
            changeColor({ 1, 0, 1 }) -- purple
        elseif gnssRtk == 1 then
            changeColor({ 0, 0, 1 }) -- blue
            GNSSReady = true
        elseif gnssRtk == 2 then
            changeColor({ 0, 1, 0 }) -- green
            GNSSReady = true
        end
        selfState = state.idle
    end
end

local function checkOriginPosition()
    if selfState == state.idle then
        selfState = state.inCheck
        local lpsPosition = Sensors.lpsPosition
        local x1, y1, z1 = lpsPosition() -- current position
        local x2, y2, z2 = NandLua.readPosition(curr_ind_point) -- origin position
        if (math.abs(x1 - x2) <= dist_check_position) and math.abs(y1 - y2) <= dist_check_position then
            changeColor({ 0, 1, 0 }) -- green
            onPosition = true
        else
            changeColor({ 1, 0, 0 }) -- red
        end
        selfState = state.idle
    end
end

local function emergency()
    Timer.callLater(1, function()
        changeColor({ 1, 0, 0 })
    end)
end

local function positionLoop(startTime)
    if idPoint == 1 then
        colorLoop(startTime + periodPositions, 0, 0)
    end
    local pointTime = (idPoint + 1) * periodPositions
    if selfState == state.flight and idPoint < numPositions then
        local x, y, z = NandLua.readPosition(idPoint)
        ap.goToLocalPoint(x, y, z, periodPositions)
        idPoint = idPoint + 1
        Timer.callAtGlobal(startTime + pointTime, function()
            positionLoop(startTime)
        end)
    elseif selfState == state.flight then
        Timer.callLater(1, function()
            landing()
        end)
    end
end

local function colorLoop(startTime)
    if selfState == state.flight and idColor < numColors then
        local colorTime = (idColor + 1) * periodColors
        changeColor(NandLua.readColor(idColor))
        Timer.callAtGlobal(startTime + colorTime, function()
            colorLoop(startTime)
        end)
    end
end

local function rcHandler()
    -- ch8(SWA)=[-1,-1,1]	ch7(SWB)=[0,1,2] 	ch5(SWC)=[0,1,2] 	ch6(SWD)=[1,1,0]
    -- ch1(RH)=[-1..1]		ch2(RV)=[1..-1]		ch2(LV)=[0..1]		ch4(LH)=[1..-1]
    _, _, _, _, SWC, SWD, SWB, SWA = Sensors.rc()
    if SWB == 2 and onPosition and GNSSReady and selfState == state.idle then
        syncTime = getNearestTime(15)
        selfState = state.start
        Timer.callAtGlobal(syncTime + 1, function()
            ap.push(Ev.MCE_PREFLIGHT)
        end)
        Timer.callAtGlobal(syncTime + 3, function()
            if selfState == state.start and isMotorStarted then
                selfState = state.takeoff
            end
            ap.push(Ev.MCE_TAKEOFF)
        end)
        Timer.callAtGlobal(syncTime + 10 - 0.16, function()
            positionLoop(syncTime + 10 - 0.16)
        end)
    elseif SWA == 1 and navSystem == 0 then
        getGNSSState()
    elseif SWD == 0 then
        checkOriginPosition()
    elseif selfState == state.idle then
        changeColor({ 0, 0, 0 }) -- no color
    end
end

function landing()
    selfState = state.landing
    ap.push(Ev.MCE_LANDING)
end

local function init()
    if navSystem == 0 then
        -- GPS
        local originLat, originLon, originAlt = NandLua.readPositionOrigin()
        if originLat ~= nil and originLon ~= nil and originAlt ~= nil then
            ap.setGpsOrigin(originLat, originLon, originAlt)
        end
    elseif navSystem == 1 then
        -- LPS
        GNSSReady = true
    end
end

function callback(event)
    if event == Ev.LOW_VOLTAGE2 then
        emergency()
        landing()
    elseif event == Ev.ENGINES_STARTED and selfState == state.start then
        isMotorStarted = true
    elseif event == Ev.TAKEOFF_COMPLETE and selfState == state.takeoff then
        selfState = state.flight
    elseif event == Ev.COPTER_LANDED and selfState == state.landing then
        selfState = state.idle
        isMotorStarted = false
    end

end

init()
timerRC = Timer.new(0.1, function()
    rcHandler()
end)
timerRC:start()