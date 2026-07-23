-- SRAM save data extraction
-- Dump 8KB SRAM at multiple game states to capture save structure
local poll = 0
local OUT = "/data/user/work/sram_dump"
os.execute("mkdir -p " .. OUT)

local SRAM = emu.memType.snesSaveRam
local VRAM = emu.memType.snesVram
local CRAM = emu.memType.snesCgRam
local captureIdx = 0

local function dumpSRAM(label)
  -- SRAM: 8KB (0x2000 bytes)
  local f = io.open(OUT .. "/" .. label .. "_sram.bin", "wb")
  if f then
    for i = 0, 8191 do
      f:write(string.char(emu.read(i, SRAM) & 0xFF))
    end
    f:close()
  end

  -- Also capture screen for context
  local buf = emu.getScreenBuffer()
  local sbF = io.open(OUT .. "/" .. label .. "_sb.bin", "wb")
  if sbF then
    for i = 1, #buf do sbF:write(string.char(buf[i] & 0xFF)) end
    sbF:close()
  end

  local cgF = io.open(OUT .. "/" .. label .. "_cg.bin", "wb")
  if cgF then
    for i = 0, 511 do cgF:write(string.char(emu.read(i, CRAM) & 0xFF)) end
    cgF:close()
  end

  -- Also dump WRAM page 0 for game state correlation
  local WRAM = emu.memType.snesWram
  local wf = io.open(OUT .. "/" .. label .. "_wram_page0.bin", "wb")
  if wf then
    for i = 0, 255 do wf:write(string.char(emu.read(i, WRAM) & 0xFF)) end
    wf:close()
  end

  captureIdx = captureIdx + 1

  -- Hex dump first 64 bytes of SRAM
  local hexStr = ""
  for i = 0, 63 do
    hexStr = hexStr .. string.format("%02X ", emu.read(i, SRAM) & 0xFF)
    if (i + 1) % 16 == 0 then hexStr = hexStr .. "\n        " end
  end
  print(string.format("[sram] [%d] '%s' at frame %d\n        %s", captureIdx, label, poll, hexStr))
  io.stdout:flush()
end

emu.addEventCallback(function()
  poll = poll + 1

  -- Skip intro
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

  -- Walk to world map
  elseif poll >= 7100 and poll < 11000 then
    local mp = poll - 7100
    if mp % 10 == 0 then
      if mp < 1200 then emu.setInput({ right = true }, 0, 0)
      elseif mp < 2200 then emu.setInput({ up = true }, 0, 0)
      elseif mp < 2800 then emu.setInput({ right = true }, 0, 0)
      else emu.setInput({ up = true }, 0, 0) end
    elseif mp % 10 == 5 then emu.setInput({}, 0, 0) end

  -- Walk on world map
  elseif poll >= 11000 and poll < 14000 then
    local mp = poll - 11000
    if mp % 8 == 0 then
      local phase = mp // 500
      if phase % 4 == 0 then emu.setInput({ up = true }, 0, 0)
      elseif phase % 4 == 1 then emu.setInput({ right = true }, 0, 0)
      elseif phase % 4 == 2 then emu.setInput({ down = true }, 0, 0)
      else emu.setInput({ left = true }, 0, 0) end
    else emu.setInput({}, 0, 0) end

  -- Open config with Select
  elseif poll >= 14000 and poll < 14040 then
    if poll % 20 < 10 then emu.setInput({ select = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 14040 and poll < 14500 then
    emu.setInput({}, 0, 0)
  elseif poll >= 14500 then
    emu.setInput({}, 0, 0)
  end
end, emu.eventType.inputPolled)

emu.addEventCallback(function()
  if poll == 1000 then dumpSRAM("sram_00_boot")
  elseif poll == 3000 then dumpSRAM("sram_01_title")
  elseif poll == 7200 then dumpSRAM("sram_02_town")
  elseif poll == 11000 then dumpSRAM("sram_03_worldmap")
  elseif poll == 12000 then dumpSRAM("sram_04_wm_walk1")
  elseif poll == 13000 then dumpSRAM("sram_05_wm_walk2")
  elseif poll == 14000 then dumpSRAM("sram_06_before_config")
  elseif poll == 14050 then dumpSRAM("sram_07_config_open")
  elseif poll == 14500 then dumpSRAM("sram_08_final")
  end

  if poll % 3000 == 0 then
    print(string.format("[sram] frame %d, captures=%d", poll, captureIdx))
    io.stdout:flush()
  end

  if poll == 14800 then
    print(string.format("[sram] Done! Total captures: %d", captureIdx))
    io.stdout:flush()
    emu.stop(0)
  end
end, emu.eventType.endFrame)

print("[sram] script loaded")
io.stdout:flush()
