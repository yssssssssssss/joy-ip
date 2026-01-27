'use strict'

const fs = require('node:fs')
const path = require('node:path')

const originalRename = fs.rename.bind(fs)
const originalRenameSync = fs.renameSync.bind(fs)
const originalRenamePromise = fs.promises.rename.bind(fs.promises)

async function renameWithCopyFallback(src, dest) {
  await fs.promises.mkdir(path.dirname(dest), { recursive: true })

  const stat = await fs.promises.lstat(src)

  if (stat.isDirectory()) {
    await fs.promises.cp(src, dest, { recursive: true, force: true })
    await fs.promises.rm(src, { recursive: true, force: true })
    return
  }

  if (stat.isSymbolicLink()) {
    const link = await fs.promises.readlink(src)
    try {
      await fs.promises.unlink(dest)
    } catch (e) {
      if (!e || e.code !== 'ENOENT') throw e
    }
    await fs.promises.symlink(link, dest)
    await fs.promises.unlink(src)
    return
  }

  await fs.promises.copyFile(src, dest)
  await fs.promises.unlink(src)
}

async function existsAsync(p) {
  try {
    await fs.promises.access(p)
    return true
  } catch {
    return false
  }
}

function existsSync(p) {
  try {
    fs.accessSync(p)
    return true
  } catch {
    return false
  }
}

fs.promises.rename = async function patchedRename(src, dest) {
  try {
    return await originalRenamePromise(src, dest)
  } catch (e) {
    if (e && e.code === 'EXDEV') {
      await renameWithCopyFallback(src, dest)
      return
    }
    if (e && e.code === 'ENOENT') {
      if (await existsAsync(dest)) return
    }
    throw e
  }
}

fs.rename = function patchedRenameCb(src, dest, cb) {
  return originalRename(src, dest, async (err) => {
    if (!err) {
      cb(null)
      return
    }

    try {
      if (err.code === 'EXDEV') {
        await renameWithCopyFallback(src, dest)
        cb(null)
        return
      }
      if (err.code === 'ENOENT' && (await existsAsync(dest))) {
        cb(null)
        return
      }
      cb(err)
    } catch (e) {
      cb(e)
    }
  })
}

fs.renameSync = function patchedRenameSync(src, dest) {
  try {
    return originalRenameSync(src, dest)
  } catch (e) {
    if (e && e.code === 'EXDEV') {
      fs.mkdirSync(path.dirname(dest), { recursive: true })
      const stat = fs.lstatSync(src)

      if (stat.isDirectory()) {
        fs.cpSync(src, dest, { recursive: true, force: true })
        fs.rmSync(src, { recursive: true, force: true })
        return
      }

      if (stat.isSymbolicLink()) {
        const link = fs.readlinkSync(src)
        try {
          fs.unlinkSync(dest)
        } catch (err2) {
          if (!err2 || err2.code !== 'ENOENT') throw err2
        }
        fs.symlinkSync(link, dest)
        fs.unlinkSync(src)
        return
      }

      fs.copyFileSync(src, dest)
      fs.unlinkSync(src)
      return
    }

    if (e && e.code === 'ENOENT') {
      if (existsSync(dest)) return
    }

    throw e
  }
}
