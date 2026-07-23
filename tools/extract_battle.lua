-- Battle scene VRAM + OAM + CGRAM extraction
-- Navigate to world map, trigger random encounter, capture battle data
local poll = 0
local OUT = "/data/user/work/battle_vram"
os.execute("mkdir -p " .. OUT)

local VRAM = emu.memType.snesVram
local CRAM = emu.memType.snesCgRam

-- Try to get OAM memory type
local OAM = nil
local oamOK = pcall(function()
  OAM = emu.memType.snesOam
end)
if not oamOK then
  print("[battle] snesOam not available, will skip OAM")
  OAM = nil
end
io.stdout:flush()

local captureIdx = 0
local prevSig = 0
local lastCapFrame = 0
local inBattle = false
local battleStartFrame = 0
local transitionCooldown = 0

local function computeScreenSig()
  local buf = emu.getScreenBuffer()
  local sig = 0
  for i = 1, #buf, 20 do
    sig = sig + (buf[i] & 0xFF)
  end
  return sig
end

local function dumpAll(label)
  -- VRAM
  local f = io.open(OUT .. "/" .. label .. "_vram.bin", "wb")
  if f then
    for i = 0, 65535 do
      f:write(string.char(emu.read(i, VRAM) & 0xFF))
    end
    f:close()
  end

  -- CGRAM
  local cgF = io.open(OUT .. "/" .. label .. "_cg.bin", "wb")
  if cgF then
    for i = 0, 511 do
      cgF:write(string.char(emu.read(i, CRAM) & 0xFF))
    end
    cgF:close()
  end

  -- OAM (544 bytes if available)
  if OAM then
    local oamF = io.open(OUT .. "/" .. label .. "_oam.bin", "wb")
    if oamF then
      for i = 0, 543 do
        oamF:write(string.char(emu.read(i, OAM) & 0xFF))
      end
      oamF:close()
    end
  end

  -- Screen buffer
  local buf = emu.getScreenBuffer()
  local sbF = io.open(OUT .. "/" .. label .. "_sb.bin", "wb")
  if sbF then
    for i = 1, #buf do
      sbF:write(string.char(buf[i] & 0xFF))
    end
    sbF:close()
  end

  captureIdx = captureIdx + 1
  print(string.format("[battle] [%d] Captured '%s' at frame %d (battle=%s)", captureIdx, label, poll, tostring(inBattle)))
  io.stdout:flush()
end

-- Input handling
emu.addEventCallback(function()
  poll = poll + 1

  -- === Skip to world map (frames 3000-11000) ===
  if poll >= 3000 and poll < 3040 then
    local p = (poll - 3000) % 60
    if p < 18 then emu.setInput({ start = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 3120 and poll < 3200 then
    local p = (poll - 3120) % 50
    if p < 12 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 3200 and poll < 6800 then
    local p = (poll - 3200) % 30
    if p < 10 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 7000 and poll < 7100 then
    local p = (poll - 7000) % 50
    if p < 12 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- === Exit town to world map (7100-11000) ===
  elseif poll >= 7100 and poll < 11000 then
    local mp = poll - 7100
    if mp % 10 == 0 then
      if mp < 1200 then emu.setInput({ right = true }, 0, 0)
      elseif mp < 2200 then emu.setInput({ up = true }, 0, 0)
      elseif mp < 2800 then emu.setInput({ right = true }, 0, 0)
      else emu.setInput({ up = true }, 0, 0) end
    elseif mp % 10 == 5 then emu.setInput({}, 0, 0) end

  -- === Walk on world map to trigger encounter (11000-18500) ===
  -- Walk in patterns to maximize encounter chance
  elseif poll >= 11000 and poll < 18500 then
    local mp = poll - 11000
    -- Walk in different directions to explore and trigger battles
    if mp % 8 == 0 then
      local phase = mp // 1000
      if phase % 4 == 0 then emu.setInput({ up = true }, 0, 0)
      elseif phase % 4 == 1 then emu.setInput({ right = true }, 0, 0)
      elseif phase % 4 == 2 then emu.setInput({ down = true }, 0, 0)
      else emu.setInput({ left = true }, 0, 0) end
    else
      emu.setInput({}, 0, 0)
    end

  -- === Battle handling (if in battle, press A to advance) ===
  elseif poll >= 18500 and poll < 19500 then
    -- If still walking, try pressing A for any encounter
    local p = (poll - 18500) % 20
    if p < 5 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Stop
  elseif poll >= 19500 then
    emu.setInput({}, 0, 0)
  end
end, emu.eventType.inputPolled)

-- Capture and monitoring
emu.addEventCallback(function()
  -- Capture at key navigation milestones
  if poll == 7200 then dumpAll("wm_00_town_exit")
  elseif poll == 11000 then dumpAll("wm_01_worldmap_start")
  elseif poll == 11500 then dumpAll("wm_02_explore_n")
  elseif poll == 12000 then dumpAll("wm_03_explore_e")
  elseif poll == 12500 then dumpAll("wm_04_explore_s")
  elseif poll == 13000 then dumpAll("wm_05_explore_w")
  elseif poll == 13500 then dumpAll("wm_06_explore_n2")
  elseif poll == 14000 then dumpAll("wm_07_explore_e2")
  elseif poll == 14500 then dumpAll("wm_08_explore_s2")
  elseif poll == 15000 then dumpAll("wm_09_explore_w2")
  elseif poll == 15500 then dumpAll("wm_10_explore_n3")
  elseif poll == 16000 then dumpAll("wm_11_explore_e3")
  elseif poll == 16500 then dumpAll("wm_12_explore_s3")
  elseif poll == 17000 then dumpAll("wm_13_explore_w3")
  elseif poll == 17500 then dumpAll("wm_14_explore_n4")
  elseif poll == 18000 then dumpAll("wm_15_explore_final")
  elseif poll == 18500 then dumpAll("wm_16_final_walk")
  elseif poll == 19000 then dumpAll("wm_17_end")
  end

  -- Transition detection: capture when screen changes significantly
  if poll > 11000 and poll < 19000 and transitionCooldown == 0 then
    local sig = computeScreenSig()
    if prevSig > 0 and math.abs(sig - prevSig) > prevSig * 0.35 then
      if poll - lastCapFrame > 150 then
        dumpAll(string.format("encounter_%d", captureIdx + 1))
        lastCapFrame = poll
        transitionCooldown = 300
        -- Mark potential battle start
        if not inBattle then
          inBattle = true
          battleStartFrame = poll
          print(string.format("[battle] Potential battle detected at frame %d!", poll))
          io.stdout:flush()
        else
          -- If was in battle and screen changes again, might be battle end
          if poll - battleStartFrame > 500 then
            inBattle = false
            print(string.format("[battle] Potential battle ended at frame %d", poll))
            io.stdout:flush()
          end
        end
      end
    end
    prevSig = sig
  end

  if transitionCooldown > 0 then transitionCooldown = transitionCooldown - 1 end

  -- Progress logging
  if poll % 2000 == 0 then
    print(string.format("[battle] frame %d, captures=%d, inBattle=%s", poll, captureIdx, tostring(inBattle)))
    io.stdout:flush()
  end

  -- Stop
  if poll == 19500 then
    print(string.format("[battle] Done! Total captures: %d", captureIdx))
    io.stdout:flush()
    emu.stop(0)
  end
end, emu.eventType.endFrame)

print("[battle] script loaded, OAM=" .. tostring(oamOK))
io.stdout:flush()
