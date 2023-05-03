local unpack = table.unpack
local ledNumber = 29
local leds = Ledbar.new(ledNumber)
local numRows = 4

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
local loopStartTime = 15
local dist_check_position = 0.5
local logPos = 0

local function changeColor(col)
    for i = 0, ledNumber - 1, 1 do
        leds:set(i, unpack(col))
    end
end

local function logMessage(str)
    local curTime = string.format("%.6f ", time())
    local curTimeLen = string.len(curTime)
    LuaLog.write(logPos, curTime, curTimeLen)
    logPos = logPos + curTimeLen
    local strLen = string.len(str)
    LuaLog.write(logPos, str .. "\n", strLen + 1)
    logPos = logPos + strLen + 1
    LuaLog.sync()
end

local function getNearestTime(sec)
    if navSystem == 0 then
        return 18 + sec * (math.floor((time() + deltaTime() - 18) / sec) + 1)
    elseif navSystem == 1 then
        local dt = deltaTime()
        logMessage(string.format("deltaTime = %.6f", dt))
        return sec * (math.floor((time() + deltaTime()) / sec) + 1)
    end
end

local function snake()
    if selfState == state.idle then
        selfState = state.inCheck
        local blinkTime = 0.3
        local snakeTime = getNearestTime(10)
        changeColor({ 0, 1, 1 })
        Timer.callAtGlobal(snakeTime, function()
            changeColor({ 0, 0, 0 })
        end)
        Timer.callAtGlobal(snakeTime + (boardNumber % numRows) * blinkTime, function()
            changeColor({ 1, 1, 1 })
        end)
        Timer.callAtGlobal(snakeTime + (boardNumber % numRows + 1) * blinkTime, function()
            changeColor({ 0, 0, 0 })
        end)
        Timer.callAtGlobal(snakeTime + (numRows + 1) * blinkTime + (boardNumber / numRows - (boardNumber / numRows) % 1) * blinkTime, function()
            changeColor({ 1, 1, 1 })
        end)
        Timer.callAtGlobal(snakeTime + (numRows + 1) * blinkTime + (boardNumber / numRows - (boardNumber / numRows) % 1 + 1) * blinkTime, function()
            selfState = state.idle
            changeColor({ 0, 0, 0 })
        end)
    end
end

local function checkOriginPosition()
    if selfState == state.idle then
        selfState = state.inCheck
        if navSystem == 1 then
            local lpsPosition = Sensors.lpsPosition
            local x1, y1, z1 = lpsPosition() -- current position
            local x2, y2, z2 = NandLua.readPosition(curr_ind_point) -- origin position
            if (math.abs(x1 - x2) <= dist_check_position) and math.abs(y1 - y2) <= dist_check_position then
                changeColor({ 0, 1, 0 }) -- green
                onPosition = true
            else
                changeColor({ 1, 0, 0 }) -- red
            end
        elseif navSystem == 0 then
            ap.push(Ev.MISSION_CHECK_START_POS)
        end
        selfState = state.idle
    end
end

local function emergency()
    Timer.callLater(1, function()
        changeColor({ 1, 0, 0 })
    end)
end

function landing()
    selfState = state.landing
    ap.push(Ev.MCE_LANDING)
end

local function colorLoop(startTime)
    if selfState == state.flight and idColor < numColors then
        local colorTime = (idColor + 1) * periodColors
        changeColor({ NandLua.readColor(idColor) })
        idColor = idColor + 1
        Timer.callAtGlobal(startTime + colorTime, function()
            colorLoop(startTime)
        end)
    end
end

local function positionLoop(startTime)

    if idPoint == 0 then
        colorLoop(startTime)
    end

    local pointTime = (idPoint + 1) * periodPositions
    if selfState == state.flight and idPoint < numPositions then
        local x, y, z = NandLua.readPosition(idPoint)
        ap.goToLocalPoint(x, y, z, periodPositions)
        logMessage(string.format("point #%d", idPoint))
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

local function rcHandler()
    -- ch8(SWA)=[-1,-1,1]	ch7(SWB)=[0,1,2] 	ch5(SWC)=[0,1,2] 	ch6(SWD)=[1,1,0]
    -- ch1(RH)=[-1..1]		ch2(RV)=[1..-1]		ch2(LV)=[0..1]		ch4(LH)=[1..-1]
    _, _, _, _, SWC, SWD, SWB, SWA = Sensors.rc()
    if SWB == 2 and onPosition and GNSSReady and selfState == state.idle then
        syncTime = getNearestTime(15)
        logMessage(string.format("syncTime = %.6f", syncTime))
        selfState = state.start

        Timer.callAtGlobal(syncTime + 1, function()
            ap.push(Ev.MCE_PREFLIGHT)
            logMessage("MCE_PREFLIGHT pushed")
        end)

        Timer.callAtGlobal(syncTime + 3, function()
            if selfState == state.start and isMotorStarted then
                selfState = state.takeoff
                ap.push(Ev.MCE_TAKEOFF)
                logMessage("MCE_TAKEOFF pushed")
            end

        end)

        Timer.callAtGlobal(syncTime + loopStartTime - 0.16, function()
            positionLoop(syncTime + loopStartTime - 0.16)
        end)
    elseif SWD == 0 and SWC == 2 then
        snake()
    --elseif SWA == 1 and navSystem == 0 then
        --getGNSSState()
    elseif SWD == 0 then
        checkOriginPosition()
    elseif selfState == state.idle then
        changeColor({ 0, 0, 0 }) -- no color

    end
end

local function init()
    if navSystem == 0 then
        -- GPS
        local x, y, z = NandLua.readPosition(0)
        ap.setFirstPoint(x, y, z)
        GNSSReady = false
    elseif navSystem == 1 then
        -- LPS
        GNSSReady = true
        loopStartTime = 7
    end
    log.enable(true)
    LuaLog.clear()
    logMessage("Init is completed")
end

function callback(event)
    if event == Ev.LOW_VOLTAGE2 then
        logMessage("LOW_VOLTAGE2 event")
        emergency()
        landing()

    elseif event == Ev.ENGINES_STARTED and selfState == state.start then
        isMotorStarted = true
        logMessage("ENGINES_STARTED event")

    elseif event == Ev.TAKEOFF_COMPLETE and selfState == state.takeoff then
        selfState = state.flight
        logMessage("TAKEOFF_COMPLETE event")

    elseif event == Ev.COPTER_LANDED and selfState == state.landing then
        logMessage("COPTER_LANDED event")
        onPosition = false
        selfState = state.idle
        idPoint = 0
        changeColor({ 0, 0, 0 })
        isMotorStarted = false
        log.enable(false)
    elseif event == Ev.MISSION_START_POS_CORRECT then
        logMessage("MISSION_START_POS_CORRECT event")
        onPosition = true
        changeColor({ 0, 1, 0 }) -- green
    elseif event == Ev.MISSION_START_POS_WRONG then
        logMessage("MISSION_START_POS_WRONG event")
        onPosition = false
        changeColor({ 1, 0, 0 }) -- red
    end

end

init()
timerRC = Timer.new(0.2, function()
    rcHandler()
end)
timerRC:start()