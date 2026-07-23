-- Extended BRR audio extraction from multiple game scenes
-- Dump SPC700 RAM/DSP at title, town, world map, config menu, transitions
local poll = 0
local OUT = "/data/user/work/brr_extended"
os.execute("mkdir -p " .. OUT)

local SPCRAM = emu.memType.snesSpcRam
local SPCROM = emu.memType.snesSpcRom
local DSPREG = emu.memType.snesSpcDspRegs
local captureIdx = 0

local function dumpSPC(label)
  -- SPC RAM: 64KB
  local rf = io.open(OUT .. "/" .. label .. "_spcRam.bin", "wb")
  if rf then
    for i = 0, 65535 do rf:write(string.char(emu.read(i, SPCRAM) & 0xFF)) end
    rf:close()
  end
  -- SPC ROM: 64KB
  local romf = io.open(OUT .. "/" .. label .. "_spcRom.bin", "wb")
  if romf then
    for i = 0, 65535 do romf:write(string.char(emu.read(i, SPCROM) & 0xFF)) end
    romf:close()
  end
  -- DSP registers: 128 bytes
  local df = io.open(OUT .. "/" .. label .. "_dspRegs.bin", "wb")
  if df then
    for i = 0, 127 do df:write(string.char(emu.read(i, DSPREG) & 0xFF)) end
    df:close()
  end
  -- Also dump VRAM + CGRAM for scene identification
  local VRAM = emu.memType.snesVram
  local CRAM = emu.memType.snesCgRam
  local vf = io.open(OUT .. "/" .. label .. "_vram.bin", "wb")
  if vf then
    for i = 0, 65535 do vf:write(string.char(emu.read(i, VRAM) & 0xFF)) end
    vf:close()
  end
  local cf = io.open(OUT .. "/" .. label .. "_cg.bin", "wb")
  if cf then
    for i = 0, 511 do cf:write(string.char(emu.read(i, CRAM) & 0xFF)) end
    cf:close()
  end
  local buf = emu.getScreenBuffer()
  local sf = io.open(OUT .. "/" .. label .. "_sb.bin", "wb")
  if sf then
    for i = 1, #buf do sf:write(string.char(buf[i] & 0xFF)) end
    sf:close()
  end

  captureIdx = captureIdx + 1
  print(string.format("[brr] [%d] Captured '%s' at frame %d", captureIdx, label, poll))
  io.stdout:flush()
end

-- Input handling
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

  -- Exit town to world map
  elseif poll >= 7100 and poll < 11000 then
    local mp = poll - 7100
    if mp % 10 == 0 then
      if mp < 1200 then emu.setInput({ right = true }, 0, 0)
      elseif mp < 2200 then emu.setInput({ up = true }, 0, 0)
      elseif mp < 2800 then emu.setInput({ right = true }, 0, 0)
      else emu.setInput({ up = true }, 0, 0) end
    elseif mp % 10 == 5 then emu.setInput({}, 0, 0) end

  -- Walk on world map
  elseif poll >= 11000 and poll < 12400 then
    local mp = poll - 11000
    if mp % 8 == 0 then
      local phase = mp // 400
      if phase % 4 == 0 then emu.setInput({ up = true }, 0, 0)
      elseif phase % 4 == 1 then emu.setInput({ right = true }, 0, 0)
      elseif phase % 4 == 2 then emu.setInput({ down = true }, 0, 0)
      else emu.setInput({ left = true }, 0, 0) end
    else emu.setInput({}, 0, 0) end

  -- Open config menu with Select
  elseif poll >= 12400 and poll < 12440 then
    if poll % 20 < 10 then emu.setInput({ select = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Navigate config menu
  elseif poll >= 12440 and poll < 12600 then
    local mp = poll - 12440
    if mp % 20 < 5 then
      if mp // 40 % 2 == 0 then emu.setInput({ down = true }, 0, 0)
      else emu.setInput({ up = true }, 0, 0) end
    else emu.setInput({}, 0, 0) end

  -- Close config
  elseif poll >= 12600 and poll < 12640 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Walk more
  elseif poll >= 12640 and poll < 14000 then
    local mp = poll - 12640
    if mp % 8 == 0 then
      local phase = mp // 500
      if phase % 4 == 0 then emu.setInput({ up = true }, 0, 0)
      elseif phase % 4 == 1 then emu.setInput({ right = true }, 0, 0)
      elseif phase % 4 == 2 then emu.setInput({ down = true }, 0, 0)
      else emu.setInput({ left = true }, 0, 0) end
    else emu.setInput({}, 0, 0) end

  -- Try Start
  elseif poll >= 14000 and poll < 14040 then
    if poll % 20 < 10 then emu.setInput({ start = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 14040 and poll < 14200 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 14200 then
    emu.setInput({}, 0, 0)
  end
end, emu.eventType.inputPolled)

-- Capture SPC at key moments
emu.addEventCallback(function()
  if poll == 3000 then dumpSPC("spc_00_title")
  elseif poll == 6800 then dumpSPC("spc_01_intro_end")
  elseif poll == 7200 then dumpSPC("spc_02_town")
  elseif poll == 11000 then dumpSPC("spc_03_wm_entry")
  elseif poll == 11700 then dumpSPC("spc_04_wm_walk1")
  elseif poll == 12400 then dumpSPC("spc_05_before_config")
  elseif poll == 12450 then dumpSPC("spc_06_config_open")
  elseif poll == 12550 then dumpSPC("spc_07_config_nav")
  elseif poll == 12620 then dumpSPC("spc_08_config_closed")
  elseif poll == 13200 then dumpSPC("spc_09_wm_terrain1")
  elseif poll == 14040 then dumpSPC("spc_10_after_start")
  elseif poll == 14200 then dumpSPC("spc_11_final")
  end

  if poll % 2000 == 0 then
    print(string.format("[brr] frame %d, captures=%d", poll, captureIdx))
    io.stdout:flush()
  end

  if poll == 14500 then
    print(string.format("[brr] Done! Total captures: %d", captureIdx))
    io.stdout:flush()
    emu.stop(0)
  end
end, emu.eventType.endFrame)

print("[brr] script loaded")
io.stdout:flush()
