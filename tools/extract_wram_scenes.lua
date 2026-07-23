-- Comprehensive WRAM extraction across multiple game scenes
-- Capture 128KB WRAM at title, town, world map, menu states
local poll = 0
local OUT = "/data/user/work/wram_scenes"
os.execute("mkdir -p " .. OUT)

local WRAM = emu.memType.snesWram
local VRAM = emu.memType.snesVram
local CRAM = emu.memType.snesCgRam
local captureIdx = 0

local function dumpWRAM(label)
  local f = io.open(OUT .. "/" .. label .. "_wram.bin", "wb")
  if f then
    -- SNES WRAM is 128KB (0x20000 bytes)
    for i = 0, 131071 do
      f:write(string.char(emu.read(i, WRAM) & 0xFF))
    end
    f:close()
  end

  -- Also capture VRAM and CGRAM for correlation
  local vf = io.open(OUT .. "/" .. label .. "_vram.bin", "wb")
  if vf then
    for i = 0, 65535 do
      vf:write(string.char(emu.read(i, VRAM) & 0xFF))
    end
    vf:close()
  end

  local cgF = io.open(OUT .. "/" .. label .. "_cg.bin", "wb")
  if cgF then
    for i = 0, 511 do
      cgF:write(string.char(emu.read(i, CRAM) & 0xFF))
    end
    cgF:close()
  end

  local buf = emu.getScreenBuffer()
  local sbF = io.open(OUT .. "/" .. label .. "_sb.bin", "wb")
  if sbF then
    for i = 1, #buf do
      sbF:write(string.char(buf[i] & 0xFF))
    end
    sbF:close()
  end

  captureIdx = captureIdx + 1
  print(string.format("[wram] [%d] Captured '%s' at frame %d", captureIdx, label, poll))
  io.stdout:flush()
end

emu.addEventCallback(function()
  poll = poll + 1

  -- === Skip intro (3000-6800) ===
  if poll >= 3000 and poll < 3040 then
    local p = (poll - 3000) % 60
    if p < 18 then emu.setInput({ start = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 3120 and poll < 3200 then
    local p = (poll - 3120) % 50
    if p < 12 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 3200 and poll < 6800 then
    local p = (poll - 3200) % 30
    if p < 10 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Close initial menu
  elseif poll >= 7000 and poll < 7100 then
    local p = (poll - 7000) % 50
    if p < 12 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- === Navigate to world map (7100-11000) ===
  elseif poll >= 7100 and poll < 11000 then
    local mp = poll - 7100
    if mp % 10 == 0 then
      if mp < 1200 then emu.setInput({ right = true }, 0, 0)
      elseif mp < 2200 then emu.setInput({ up = true }, 0, 0)
      elseif mp < 2800 then emu.setInput({ right = true }, 0, 0)
      else emu.setInput({ up = true }, 0, 0) end
    elseif mp % 10 == 5 then emu.setInput({}, 0, 0) end

  -- === Walk on world map to find different terrain (11000-12400) ===
  elseif poll >= 11000 and poll < 12400 then
    local mp = poll - 11000
    if mp % 8 == 0 then
      local phase = mp // 400
      if phase % 4 == 0 then emu.setInput({ up = true }, 0, 0)
      elseif phase % 4 == 1 then emu.setInput({ right = true }, 0, 0)
      elseif phase % 4 == 2 then emu.setInput({ down = true }, 0, 0)
      else emu.setInput({ left = true }, 0, 0) end
    else
      emu.setInput({}, 0, 0)
    end

  -- === Open config menu with Select (12400-12440) ===
  elseif poll >= 12400 and poll < 12440 then
    if poll % 20 < 10 then emu.setInput({ select = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- === Navigate in config menu (12440-12600) ===
  elseif poll >= 12440 and poll < 12600 then
    local mp = poll - 12440
    if mp % 20 < 5 then
      local phase = mp // 40
      if phase % 4 == 0 then emu.setInput({ down = true }, 0, 0)
      elseif phase % 4 == 1 then emu.setInput({ right = true }, 0, 0)
      elseif phase % 4 == 2 then emu.setInput({ up = true }, 0, 0)
      else emu.setInput({ left = true }, 0, 0) end
    else
      emu.setInput({}, 0, 0)
    end

  -- === Close config menu with B (12600-12640) ===
  elseif poll >= 12600 and poll < 12640 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- === Walk some more, capture different terrain (12640-14000) ===
  elseif poll >= 12640 and poll < 14000 then
    local mp = poll - 12640
    if mp % 8 == 0 then
      local phase = mp // 500
      if phase % 4 == 0 then emu.setInput({ up = true }, 0, 0)
      elseif phase % 4 == 1 then emu.setInput({ right = true }, 0, 0)
      elseif phase % 4 == 2 then emu.setInput({ down = true }, 0, 0)
      else emu.setInput({ left = true }, 0, 0) end
    else
      emu.setInput({}, 0, 0)
    end

  -- === Try Start button for save menu (14000-14040) ===
  elseif poll >= 14000 and poll < 14040 then
    if poll % 20 < 10 then emu.setInput({ start = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- === Close and stop (14040+) ===
  elseif poll >= 14040 and poll < 14200 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 14200 then
    emu.setInput({}, 0, 0)
  end
end, emu.eventType.inputPolled)

-- Scheduled captures at key scene transitions
emu.addEventCallback(function()
  -- Title screen
  if poll == 3000 then dumpWRAM("scene_00_title")
  -- Intro skip
  elseif poll == 6800 then dumpWRAM("scene_01_intro_end")
  -- Town
  elseif poll == 7200 then dumpWRAM("scene_02_town")
  -- World map entry
  elseif poll == 11000 then dumpWRAM("scene_03_wm_entry")
  -- World map north
  elseif poll == 11400 then dumpWRAM("scene_04_wm_north")
  -- World map east
  elseif poll == 11800 then dumpWRAM("scene_05_wm_east")
  -- World map south
  elseif poll == 12200 then dumpWRAM("scene_06_wm_south")
  -- Before config menu
  elseif poll == 12400 then dumpWRAM("scene_07_before_config")
  -- Config menu open
  elseif poll == 12450 then dumpWRAM("scene_08_config_open")
  -- Config menu navigating
  elseif poll == 12500 then dumpWRAM("scene_09_config_nav1")
  elseif poll == 12550 then dumpWRAM("scene_10_config_nav2")
  -- Config menu closed
  elseif poll == 12620 then dumpWRAM("scene_11_config_closed")
  -- World map after config
  elseif poll == 12800 then dumpWRAM("scene_12_wm_after_config")
  -- Different terrain 1
  elseif poll == 13200 then dumpWRAM("scene_13_terrain1")
  -- Different terrain 2
  elseif poll == 13600 then dumpWRAM("scene_14_terrain2")
  -- After Start button
  elseif poll == 14040 then dumpWRAM("scene_15_after_start")
  -- Final idle
  elseif poll == 14200 then dumpWRAM("scene_16_final")
  end

  -- Progress logging
  if poll % 2000 == 0 then
    print(string.format("[wram] frame %d, captures=%d", poll, captureIdx))
    io.stdout:flush()
  end

  -- Stop
  if poll == 14500 then
    print(string.format("[wram] Done! Total captures: %d", captureIdx))
    io.stdout:flush()
    emu.stop(0)
  end
end, emu.eventType.endFrame)

print("[wram] script loaded")
io.stdout:flush()
