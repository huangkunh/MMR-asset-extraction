-- Comprehensive menu system VRAM extraction
-- Navigate through all menu options: status, equipment, items, config
-- Capture VRAM at each menu state
local poll = 0
local OUT = "/data/user/work/menu_system"
os.execute("mkdir -p " .. OUT)

local VRAM = emu.memType.snesVram
local CRAM = emu.memType.snesCgRam

local captureIdx = 0

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
  print(string.format("[menu] [%d] Captured '%s' at frame %d", captureIdx, label, poll))
  io.stdout:flush()
end

-- Input handling
emu.addEventCallback(function()
  poll = poll + 1

  -- === Skip to town (3000-7100) ===
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

  -- === Open menu with X button (7200) ===
  elseif poll >= 7200 and poll < 7240 then
    if poll % 20 < 10 then emu.setInput({ x = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- === Menu navigation: capture each menu state ===
  -- State 0: Main menu open (7300)
  -- State 1: Navigate down through options (7400-8000)
  -- State 2: Press A on each option to open submenu

  -- Wait for menu to open
  elseif poll >= 7240 and poll < 7300 then
    emu.setInput({}, 0, 0)

  -- Capture main menu, then navigate down
  elseif poll >= 7300 and poll < 7340 then
    emu.setInput({}, 0, 0)  -- Let menu settle
  elseif poll >= 7340 and poll < 7380 then
    -- Press down to move to 2nd option
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 7380 and poll < 7420 then
    emu.setInput({}, 0, 0)

  -- Press A on 2nd option (equipment?)
  elseif poll >= 7420 and poll < 7460 then
    if poll % 20 < 5 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 7460 and poll < 7500 then
    emu.setInput({}, 0, 0)

  -- Close submenu with B
  elseif poll >= 7500 and poll < 7540 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 7540 and poll < 7580 then
    emu.setInput({}, 0, 0)

  -- Navigate down to 3rd option
  elseif poll >= 7580 and poll < 7620 then
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 7620 and poll < 7660 then
    emu.setInput({}, 0, 0)

  -- Press A on 3rd option (items?)
  elseif poll >= 7660 and poll < 7700 then
    if poll % 20 < 5 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 7700 and poll < 7740 then
    emu.setInput({}, 0, 0)

  -- Close with B
  elseif poll >= 7740 and poll < 7780 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 7780 and poll < 7820 then
    emu.setInput({}, 0, 0)

  -- Navigate down to 4th option
  elseif poll >= 7820 and poll < 7860 then
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 7860 and poll < 7900 then
    emu.setInput({}, 0, 0)

  -- Press A on 4th option
  elseif poll >= 7900 and poll < 7940 then
    if poll % 20 < 5 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 7940 and poll < 7980 then
    emu.setInput({}, 0, 0)

  -- Close with B
  elseif poll >= 7980 and poll < 8020 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8020 and poll < 8060 then
    emu.setInput({}, 0, 0)

  -- Navigate down to 5th option
  elseif poll >= 8060 and poll < 8100 then
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8100 and poll < 8140 then
    emu.setInput({}, 0, 0)

  -- Press A on 5th option
  elseif poll >= 8140 and poll < 8180 then
    if poll % 20 < 5 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8180 and poll < 8220 then
    emu.setInput({}, 0, 0)

  -- Close with B
  elseif poll >= 8220 and poll < 8260 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8260 and poll < 8300 then
    emu.setInput({}, 0, 0)

  -- Navigate down to 6th option (if exists)
  elseif poll >= 8300 and poll < 8340 then
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8340 and poll < 8380 then
    emu.setInput({}, 0, 0)

  -- Press A on 6th option
  elseif poll >= 8380 and poll < 8420 then
    if poll % 20 < 5 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8420 and poll < 8460 then
    emu.setInput({}, 0, 0)

  -- Close with B, then close main menu
  elseif poll >= 8460 and poll < 8500 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8500 and poll < 8540 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8540 and poll < 8600 then
    emu.setInput({}, 0, 0)

  -- === Open menu again and try Start button for different menu ===
  elseif poll >= 8600 and poll < 8640 then
    if poll % 20 < 10 then emu.setInput({ x = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8640 and poll < 8700 then
    emu.setInput({}, 0, 0)

  -- Navigate up in menu (try first option - might be status)
  elseif poll >= 8700 and poll < 8740 then
    if poll % 20 < 5 then emu.setInput({ up = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8740 and poll < 8780 then
    emu.setInput({}, 0, 0)

  -- Press A on first option (status?)
  elseif poll >= 8780 and poll < 8820 then
    if poll % 20 < 5 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8820 and poll < 8900 then
    emu.setInput({}, 0, 0)

  -- Press A to advance any dialog
  elseif poll >= 8900 and poll < 8940 then
    if poll % 20 < 5 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 8940 and poll < 8980 then
    emu.setInput({}, 0, 0)

  -- Close everything
  elseif poll >= 8980 and poll < 9020 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 9020 and poll < 9060 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 9060 and poll < 9100 then
    emu.setInput({}, 0, 0)

  -- === Try Start button menu (config/save?) ===
  elseif poll >= 9100 and poll < 9140 then
    if poll % 20 < 10 then emu.setInput({ start = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 9140 and poll < 9200 then
    emu.setInput({}, 0, 0)

  -- Navigate in start menu
  elseif poll >= 9200 and poll < 9240 then
    if poll % 20 < 5 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 9240 and poll < 9280 then
    emu.setInput({}, 0, 0)

  -- Press A
  elseif poll >= 9280 and poll < 9320 then
    if poll % 20 < 5 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 9320 and poll < 9380 then
    emu.setInput({}, 0, 0)

  -- Close
  elseif poll >= 9380 and poll < 9420 then
    if poll % 20 < 5 then emu.setInput({ b = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 9420 and poll < 9500 then
    emu.setInput({}, 0, 0)

  -- === CGRAM animation detection: capture CGRAM every 5 frames ===
  -- This phase runs from 9500 to 12000
  elseif poll >= 9500 and poll < 12000 then
    emu.setInput({}, 0, 0)

  -- Stop
  elseif poll >= 12000 then
    emu.setInput({}, 0, 0)
  end
end, emu.eventType.inputPolled)

-- Capture and monitoring
emu.addEventCallback(function()
  -- Menu state captures
  if poll == 7300 then dumpAll("menu_00_main")
  elseif poll == 7380 then dumpAll("menu_01_nav_down1")
  elseif poll == 7460 then dumpAll("menu_02_submenu_2nd")
  elseif poll == 7540 then dumpAll("menu_03_back_main")
  elseif poll == 7620 then dumpAll("menu_04_nav_down2")
  elseif poll == 7700 then dumpAll("menu_05_submenu_3rd")
  elseif poll == 7780 then dumpAll("menu_06_back_main2")
  elseif poll == 7860 then dumpAll("menu_07_nav_down3")
  elseif poll == 7940 then dumpAll("menu_08_submenu_4th")
  elseif poll == 8020 then dumpAll("menu_09_back_main3")
  elseif poll == 8100 then dumpAll("menu_10_nav_down4")
  elseif poll == 8180 then dumpAll("menu_11_submenu_5th")
  elseif poll == 8260 then dumpAll("menu_12_back_main4")
  elseif poll == 8340 then dumpAll("menu_13_nav_down5")
  elseif poll == 8420 then dumpAll("menu_14_submenu_6th")
  elseif poll == 8500 then dumpAll("menu_15_closing")
  elseif poll == 8600 then dumpAll("menu_16_closed")
  elseif poll == 8700 then dumpAll("menu_17_reopen")
  elseif poll == 8780 then dumpAll("menu_18_nav_up")
  elseif poll == 8820 then dumpAll("menu_19_submenu_1st")
  elseif poll == 8900 then dumpAll("menu_20_submenu_adv")
  elseif poll == 8980 then dumpAll("menu_21_closing2")
  elseif poll == 9100 then dumpAll("menu_22_start_menu")
  elseif poll == 9200 then dumpAll("menu_23_start_nav")
  elseif poll == 9280 then dumpAll("menu_24_start_select")
  elseif poll == 9380 then dumpAll("menu_25_start_close")
  elseif poll == 9500 then dumpAll("menu_26_idle")
  end

  -- CGRAM animation detection: capture CGRAM every 5 frames from 9500 to 10000
  if poll >= 9500 and poll < 10000 and (poll - 9500) % 5 == 0 then
    local cgF = io.open(OUT .. string.format("/cgram_anim_%04d.bin", poll - 9500), "wb")
    if cgF then
      for i = 0, 511 do
        cgF:write(string.char(emu.read(i, CRAM) & 0xFF))
      end
      cgF:close()
    end
  end

  -- Progress logging
  if poll % 2000 == 0 then
    print(string.format("[menu] frame %d, captures=%d", poll, captureIdx))
    io.stdout:flush()
  end

  -- Stop
  if poll == 12000 then
    print(string.format("[menu] Done! Total captures: %d + CGRAM animation frames", captureIdx))
    io.stdout:flush()
    emu.stop(0)
  end
end, emu.eventType.endFrame)

print("[menu] script loaded")
io.stdout:flush()
