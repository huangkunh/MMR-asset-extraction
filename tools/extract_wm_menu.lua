-- World map menu VRAM extraction
-- Navigate to world map, open menu, navigate through options
-- The menu likely opens with X button on the world map (not inside buildings)
local poll = 0
local OUT = "/data/user/work/wm_menu"
os.execute("mkdir -p " .. OUT)

local VRAM = emu.memType.snesVram
local CRAM = emu.memType.snesCgRam
local captureIdx = 0
local prevSig = 0
local lastCapFrame = 0
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
  local f = io.open(OUT .. "/" .. label .. "_vram.bin", "wb")
  if f then
    for i = 0, 65535 do
      f:write(string.char(emu.read(i, VRAM) & 0xFF))
    end
    f:close()
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
  print(string.format("[wmmenu] [%d] Captured '%s' at frame %d", captureIdx, label, poll))
  io.stdout:flush()
end

-- Input handling
emu.addEventCallback(function()
  poll = poll + 1

  -- === Skip to world map (3000-11000) ===
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

  -- === On world map: try opening menu with X (11000) ===
  elseif poll >= 11000 and poll < 11040 then
    if poll % 20 < 10 then emu.setInput({ x = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 11040 and poll < 11100 then
    emu.setInput({}, 0, 0)

  -- === Capture menu open, then navigate down through options ===
  -- Navigate down 1
  elseif poll >= 11100 and poll < 11140 then
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 11140 and poll < 11180 then
    emu.setInput({}, 0, 0)

  -- Navigate down 2
  elseif poll >= 11180 and poll < 11220 then
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 11220 and poll < 11260 then
    emu.setInput({}, 0, 0)

  -- Navigate down 3
  elseif poll >= 11260 and poll < 11300 then
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 11300 and poll < 11340 then
    emu.setInput({}, 0, 0)

  -- Navigate down 4
  elseif poll >= 11340 and poll < 11380 then
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 11380 and poll < 11420 then
    emu.setInput({}, 0, 0)

  -- Navigate down 5
  elseif poll >= 11420 and poll < 11460 then
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 11460 and poll < 11500 then
    emu.setInput({}, 0, 0)

  -- Navigate down 6
  elseif poll >= 11500 and poll < 11540 then
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 11540 and poll < 11580 then
    emu.setInput({}, 0, 0)

  -- Press A to open selected submenu
  elseif poll >= 11580 and poll < 11620 then
    if poll % 20 < 5 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 11620 and poll < 11700 then
    emu.setInput({}, 0, 0)

  -- Close submenu with B
  elseif poll >= 11700 and poll < 11740 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 11740 and poll < 11780 then
    emu.setInput({}, 0, 0)

  -- Navigate up to try different option
  elseif poll >= 11780 and poll < 11820 then
    if poll % 20 < 5 then emu.setInput({ up = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 11820 and poll < 11860 then
    emu.setInput({}, 0, 0)

  -- Press A on this option
  elseif poll >= 11860 and poll < 11900 then
    if poll % 20 < 5 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 11900 and poll < 12000 then
    emu.setInput({}, 0, 0)

  -- Close everything
  elseif poll >= 12000 and poll < 12040 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 12040 and poll < 12080 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 12080 and poll < 12120 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- === Try Y button for menu (12100) ===
  elseif poll >= 12200 and poll < 12240 then
    if poll % 20 < 10 then emu.setInput({ y = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 12240 and poll < 12300 then
    emu.setInput({}, 0, 0)

  -- Try Select button
  elseif poll >= 12400 and poll < 12440 then
    if poll % 20 < 10 then emu.setInput({ select = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 12440 and poll < 12500 then
    emu.setInput({}, 0, 0)

  -- Close anything that opened
  elseif poll >= 12500 and poll < 12540 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- === Walk on world map and capture different terrain ===
  elseif poll >= 12600 and poll < 14000 then
    local mp = poll - 12600
    if mp % 8 == 0 then
      local phase = mp // 500
      if phase % 4 == 0 then emu.setInput({ up = true }, 0, 0)
      elseif phase % 4 == 1 then emu.setInput({ right = true }, 0, 0)
      elseif phase % 4 == 2 then emu.setInput({ down = true }, 0, 0)
      else emu.setInput({ left = true }, 0, 0) end
    else
      emu.setInput({}, 0, 0)
    end

  -- Stop
  elseif poll >= 14000 then
    emu.setInput({}, 0, 0)
  end
end, emu.eventType.inputPolled)

-- Capture and monitoring
emu.addEventCallback(function()
  -- Menu state captures
  if poll == 11000 then dumpAll("wm_00_before_menu")
  elseif poll == 11100 then dumpAll("wm_01_menu_open_x")
  elseif poll == 11180 then dumpAll("wm_02_nav_down1")
  elseif poll == 11260 then dumpAll("wm_03_nav_down2")
  elseif poll == 11340 then dumpAll("wm_04_nav_down3")
  elseif poll == 11420 then dumpAll("wm_05_nav_down4")
  elseif poll == 11500 then dumpAll("wm_06_nav_down5")
  elseif poll == 11580 then dumpAll("wm_07_nav_down6")
  elseif poll == 11620 then dumpAll("wm_08_submenu_open")
  elseif poll == 11700 then dumpAll("wm_09_submenu_view")
  elseif poll == 11780 then dumpAll("wm_10_back_main_nav_up")
  elseif poll == 11860 then dumpAll("wm_11_option_select")
  elseif poll == 11900 then dumpAll("wm_12_submenu2_open")
  elseif poll == 12000 then dumpAll("wm_13_closing")
  elseif poll == 12100 then dumpAll("wm_14_closed")
  elseif poll == 12200 then dumpAll("wm_15_before_y")
  elseif poll == 12300 then dumpAll("wm_16_after_y")
  elseif poll == 12400 then dumpAll("wm_17_before_select")
  elseif poll == 12500 then dumpAll("wm_18_after_select")
  elseif poll == 12600 then dumpAll("wm_19_walking_start")

  -- World map terrain captures
  elseif poll == 13100 then dumpAll("wm_20_terrain_1")
  elseif poll == 13600 then dumpAll("wm_21_terrain_2")
  end

  -- Transition detection
  if poll > 11000 and poll < 14000 and transitionCooldown == 0 then
    local sig = computeScreenSig()
    if prevSig > 0 and math.abs(sig - prevSig) > prevSig * 0.35 then
      if poll - lastCapFrame > 100 then
        dumpAll(string.format("transition_%d", captureIdx + 1))
        lastCapFrame = poll
        transitionCooldown = 200
      end
    end
    prevSig = sig
  end

  if transitionCooldown > 0 then transitionCooldown = transitionCooldown - 1 end

  -- Progress logging
  if poll % 2000 == 0 then
    print(string.format("[wmmenu] frame %d, captures=%d", poll, captureIdx))
    io.stdout:flush()
  end

  -- Stop
  if poll == 14000 then
    print(string.format("[wmmenu] Done! Total captures: %d", captureIdx))
    io.stdout:flush()
    emu.stop(0)
  end
end, emu.eventType.endFrame)

print("[wmmenu] script loaded")
io.stdout:flush()
