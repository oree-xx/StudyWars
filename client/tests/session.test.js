import { beforeEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { getPlayerSession, normalizeQuestion, readSession, saveSession } from '../src/lib/session.js'

beforeEach(() => {
  const values = new Map()
  globalThis.sessionStorage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  }
})

test('host credentials survive a reload and are cleared for a new quiz', () => {
  const host = { roomCode: 'ABCDEF', hostToken: 'secret-host-token' }
  saveSession('host', host)
  assert.deepEqual(readSession('host'), host)
  saveSession('host', null)
  assert.equal(readSession('host'), null)
})

test('the same player resumes the same room using its original secret', () => {
  const original = getPlayerSession({ roomCode: ' abcdef ', name: ' Ada ' })
  assert.equal(original.roomCode, 'ABCDEF')
  assert.match(original.playerToken, /^[a-f0-9]{48}$/)
  assert.deepEqual(getPlayerSession(), original)
  assert.deepEqual(getPlayerSession({ roomCode: 'ABCDEF', name: 'Ada' }), original)
})

test('a different room or player name receives a different resume secret', () => {
  const first = getPlayerSession({ roomCode: 'ABCDEF', name: 'Ada' })
  const second = getPlayerSession({ roomCode: 'XYZABC', name: 'Ada' })
  const third = getPlayerSession({ roomCode: 'XYZABC', name: 'Tobi' })
  assert.notEqual(first.playerToken, second.playerToken)
  assert.notEqual(second.playerToken, third.playerToken)
})

test('corrupt and incomplete saved sessions are ignored', () => {
  sessionStorage.setItem('studywars:host', '{bad json')
  assert.equal(readSession('host'), null)
  sessionStorage.setItem('studywars:player', JSON.stringify({ roomCode: 'ABCDEF', name: 'Ada' }))
  assert.equal(readSession('player'), null)
})

test('blocked browser storage does not prevent joining a game', () => {
  globalThis.sessionStorage = {
    getItem() { throw new Error('Storage blocked') },
    setItem() { throw new Error('Storage blocked') },
  }
  assert.equal(readSession('player'), null)
  assert.match(getPlayerSession({ roomCode: 'ABCDEF', name: 'Ada' }).playerToken, /^[a-f0-9]{48}$/)
})

test('resumed countdown uses remaining server time even with a skewed device clock', (context) => {
  context.mock.method(Date, 'now', () => 1000000)
  const question = normalizeQuestion({ index: 2, server_time: 800000, ends_at: 803000, time_limit: 20 })
  assert.equal(question.deadline, 1003000)
})

test('expired snapshots never grant a new question interval', (context) => {
  context.mock.method(Date, 'now', () => 1000000)
  assert.equal(normalizeQuestion({ server_time: 800000, ends_at: 799000 }).deadline, 1000000)
  assert.equal(normalizeQuestion(null), null)
})
