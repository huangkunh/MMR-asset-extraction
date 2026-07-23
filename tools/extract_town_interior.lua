-- Town interior VRAM extraction
-- Navigate around town, enter buildings, capture VRAM at interior scenes

local poll = 0
local OUT = "/data/user/work/town_interior"
os.execute("mkdir -p " .. OUT)

local VRAM = emu.memType.snesVram
local CRAM = emu.memType.snesCgRam

-- Transition detection state
local prevSig = 0
local lastCaptureFrame = 0
local captureIdx = 0
local inTransition = false
local transitionCooldown = 0

local function computeScreenSig()
  local buf = emu.getScreenBuffer()
  local sig = 0
  for i = 1, #buf, 20 do
    sig = sig + (buf[i] & 0xFF)
  end
  return sig
end

local function dumpVRAM(label)
  local f = io.open(OUT .. "/" .. label .. "_vram.bin", "wb")
  if f then
    for i = 0, 65535 do
      f:write(string.char(emu.read(i, VRAM) & 0xFF))
    end
    f:close()
  end
  local cram = {}
  for i = 0, 511 do cram[i+1] = emu.read(i, CRAM) end
  local cgF = io.open(OUT .. "/" .. label .. "_cg.bin", "wb")
  if cgF then for i = 1, #cram do cgF:write(string.char(cram[i] & 0xFF)) end cgF:close() end
  local buf = emu.getScreenBuffer()
  local sbF = io.open(OUT .. "/" .. label .. "_sb.bin", "wb")
  if sbF then for i = 1, #buf do sbF:write(string.char(buf[i] & 0xFF)) end sbF:close() end
  captureIdx = captureIdx + 1
  print(string.format("[interior] [%d] Captured '%s' at frame %d", captureIdx, label, poll))
  io.stdout:flush()
end

-- Input handling
emu.addEventCallback(function()
  poll = poll + 1

  -- === Skip to town (frames 3000-7100) ===
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

  -- === Town exploration (frames 7200+) ===
  -- Phase 1: Walk up to find buildings (north)
  elseif poll >= 7200 and poll < 7600 then
    if poll % 8 == 0 then emu.setInput({ up = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 2: Walk right
  elseif poll >= 7600 and poll < 8000 then
    if poll % 8 == 0 then emu.setInput({ right = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 3: Walk up (try entering building)
  elseif poll >= 8000 and poll < 8500 then
    if poll % 8 == 0 then emu.setInput({ up = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 4: Walk right more
  elseif poll >= 8500 and poll < 9000 then
    if poll % 8 == 0 then emu.setInput({ right = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 5: Walk up
  elseif poll >= 9000 and poll < 9500 then
    if poll % 8 == 0 then emu.setInput({ up = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 6: Walk left
  elseif poll >= 9500 and poll < 10000 then
    if poll % 8 == 0 then emu.setInput({ left = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 7: Walk up
  elseif poll >= 10000 and poll < 10500 then
    if poll % 8 == 0 then emu.setInput({ up = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 8: Press A (interact/confirm)
  elseif poll >= 10500 and poll < 10600 then
    local p = (poll - 10500) % 40
    if p < 10 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 9: Walk down
  elseif poll >= 10600 and poll < 11000 then
    if poll % 8 == 0 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 10: Walk right
  elseif poll >= 11000 and poll < 11500 then
    if poll % 8 == 0 then emu.setInput({ right = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 11: Walk up (another building attempt)
  elseif poll >= 11500 and poll < 12500 then
    if poll % 8 == 0 then emu.setInput({ up = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 12: Walk right
  elseif poll >= 12500 and poll < 13000 then
    if poll % 8 == 0 then emu.setInput({ right = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 13: Walk up
  elseif poll >= 13000 and poll < 13500 then
    if poll % 8 == 0 then emu.setInput({ up = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 14: Press A
  elseif poll >= 13500 and poll < 13600 then
    local p = (poll - 13500) % 40
    if p < 10 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 15: Walk down (exit building if inside)
  elseif poll >= 13600 and poll < 14000 then
    if poll % 8 == 0 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 16: Walk right and up
  elseif poll >= 14000 and poll < 14500 then
    if poll % 8 == 0 then emu.setInput({ right = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 14500 and poll < 15000 then
    if poll % 8 == 0 then emu.setInput({ up = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 17: Press A (try to talk/interact)
  elseif poll >= 15000 and poll < 15100 then
    local p = (poll - 15000) % 40
    if p < 10 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 18: Walk left and up
  elseif poll >= 15100 and poll < 15600 then
    if poll % 8 == 0 then emu.setInput({ left = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 15600 and poll < 16100 then
    if poll % 8 == 0 then emu.setInput({ up = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 19: Press A
  elseif poll >= 16100 and poll < 16200 then
    local p = (poll - 16100) % 40
    if p < 10 then emu.setInput({ a = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Phase 20: Walk down, right, up
  elseif poll >= 16200 and poll < 16700 then
    if poll % 8 == 0 then emu.setInput({ down = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 16700 and poll < 17200 then
    if poll % 8 == 0 then emu.setInput({ right = true }, 0, 0) else emu.setInput({}, 0, 0) end
  elseif poll >= 17200 and poll < 18200 then
    if poll % 8 == 0 then emu.setInput({ up = true }, 0, 0) else emu.setInput({}, 0, 0) end

  -- Stop
  elseif poll >= 19500 then
    emu.setInput({}, 0, 0)
  end
end, emu.eventType.inputPolled)

-- Capture and monitoring
emu.addEventCallback(function()
  -- Scheduled captures at town exploration phases
  if poll == 7200 then dumpVRAM("town_00_start")
  elseif poll == 7600 then dumpVRAM("town_01_north")
  elseif poll == 8000 then dumpVRAM("town_02_ne")
  elseif poll == 8500 then dumpVRAM("town_03_east")
  elseif poll == 9000 then dumpVRAM("town_04_north2")
  elseif poll == 9500 then dumpVRAM("town_05_west")
  elseif poll == 10000 then dumpVRAM("town_06_nw")
  elseif poll == 10500 then dumpVRAM("town_07_interact")
  elseif poll == 11000 then dumpVRAM("town_08_south")
  elseif poll == 11500 then dumpVRAM("town_09_east2")
  elseif poll == 12500 then dumpVRAM("town_10_explore")
  elseif poll == 13000 then dumpVRAM("town_11_north3")
  elseif poll == 14000 then dumpVRAM("town_12_after_a")
  elseif poll == 14500 then dumpVRAM("town_13_east3")
  elseif poll == 15000 then dumpVRAM("town_14_north4")
  elseif poll == 15600 then dumpVRAM("town_15_west2")
  elseif poll == 16200 then dumpVRAM("town_16_after_interact")
  elseif poll == 16700 then dumpVRAM("town_17_south2")
  elseif poll == 17200 then dumpVRAM("town_18_explore2")
  elseif poll == 18200 then dumpVRAM("town_19_final")
  end

  -- Transition detection: capture when screen changes significantly
  if poll > 7200 and poll < 19000 and transitionCooldown == 0 then
    local sig = computeScreenSig()
    if prevSig > 0 and math.abs(sig - prevSig) > prevSig * 0.3 then
      -- Significant screen change detected
      if poll - lastCaptureFrame > 100 then
        dumpVRAM(string.format("transition_%d", captureIdx + 1))
        lastCaptureFrame = poll
        transitionCooldown = 200  -- 200 frames cooldown
      end
    end
    prevSig = sig
  end

  if transitionCooldown > 0 then transitionCooldown = transitionCooldown - 1 end

  -- Progress logging
  if poll % 2000 == 0 then
    print(string.format("[interior] frame %d, captures=%d", poll, captureIdx))
    io.stdout:flush()
  end

  -- Stop
  if poll == 19500 then
    print(string.format("[interior] Done! Total captures: %d", captureIdx))
    io.stdout:flush()
    emu.stop(0)
  end
end, emu.eventType.endFrame)

print("[interior] script loaded")
io.stdout:flush()
