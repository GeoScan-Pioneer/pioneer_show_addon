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

local periodColors		= 1/NandLua.readFreqColors()
local numColors			= NandLua.readNumberColors()
local periodPositions	= 1/NandLua.readFreqPositions()
local numPositions      = NandLua.readNumberPositions()
local onPosition        = false
local GNSSReady         = false
local navSystem         = getNavSystem()

local function changeColor(col)
    for i = 0, ledNumber - 1, 1 do
        leds:set(i, unpack(col))
    end
end

function getNearestTime(sec)
    return 18 + sec * (math.floor((time() + deltaTime() - 18) / sec) + 1)
end

function getGNSSState()
    GNSSReady = true
end

function checkOriginPosition()
    onPosition = true
end

local function emergency()
    Timer.callLater(1, function()
        changeColor({ 1, 0, 0 })
    end)
end

function callback(event)
    if (event == Ev.LOW_VOLTAGE2) then
        emergency()
    end
end

function rc_handler()
    _, _, _, _, ch5, ch6, ch7, ch8 = Sensors.rc()
end

function main_loop()
    if navSystem == 0 then -- GPS
        changeColor({ 1, 0, 0 })
    elseif navSystem == 1 then -- LPS
        changeColor({ 0, 1, 0 })
    end
end
timerMain = Timer.new(0.1, function()
    main_loop()
end)
timerMain:start()