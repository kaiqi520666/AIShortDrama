import { describe, expect, it, vi } from 'vitest'
import { useCanvasAutosave } from './useCanvasAutosave'

function setup(overrides = {}) {
  const store = {
    ready: true,
    saveConflict: false,
    saveStatus: 'saved',
    saveCanvas: vi.fn(async () => {}),
    ...overrides,
  }
  const autosave = useCanvasAutosave({
    store,
    getPayload: () => ({}),
    getViewport: () => ({ x: 1, y: 2, zoom: 1 }),
    confirm: vi.fn(async () => false),
    eventTarget: globalThis,
  })
  autosave.enable()
  return { store, autosave }
}

describe('canvas autosave', () => {
  it('debounces changes and clears dirty state after saving', async () => {
    vi.useFakeTimers()
    const { store, autosave } = setup()

    autosave.scheduleSave()
    autosave.scheduleSave()
    expect(autosave.dirty.value).toBe(true)
    await vi.advanceTimersByTimeAsync(800)

    expect(store.saveCanvas).toHaveBeenCalledOnce()
    expect(autosave.dirty.value).toBe(false)
    vi.useRealTimers()
  })

  it('keeps dirty state and lets the user cancel navigation after failure', async () => {
    const confirm = vi.fn(async () => false)
    const store = { ready: true, saveConflict: false, saveStatus: 'failed', saveCanvas: vi.fn(async () => { throw new Error('offline') }) }
    const autosave = useCanvasAutosave({ store, getPayload: () => ({}), confirm, eventTarget: globalThis })
    autosave.enable()
    autosave.scheduleSave()

    await expect(autosave.saveBeforeLeave()).resolves.toBe(false)
    expect(autosave.dirty.value).toBe(true)
    expect(confirm).toHaveBeenCalledOnce()
  })

  it('warns before browser unload only when data may be unsaved', () => {
    const { autosave } = setup()
    const clean = { preventDefault: vi.fn(), returnValue: undefined }
    autosave.handleBeforeUnload(clean)
    expect(clean.preventDefault).not.toHaveBeenCalled()

    autosave.scheduleSave()
    const dirty = { preventDefault: vi.fn(), returnValue: undefined }
    autosave.handleBeforeUnload(dirty)
    expect(dirty.preventDefault).toHaveBeenCalledOnce()
    expect(dirty.returnValue).toBe('')
  })
})
