/**
 * 公告弹窗配置文件
 * 支持 Markdown 格式
 */

export type NoticeConfig = {
    title: string
    content: string
    duration: number
    version: string
    alwaysShow: boolean
}

export const NOTICE_CONFIG: NoticeConfig = {
    title: "系统公告",
    content: `
欢迎使用 **JoyIP AI创作平台**！

### 重点关注
- 生成的素材需通过 https://brand.jd.com/checkchannel 审核后，才可上线使用
- plan 模式：系统会先对 prompt 进行拆解分析，你可以进行针对性修改，以获得更好效果
- 3D 素材生成：现已支持 3D 风格素材生成
- 2D 素材生成：现已支持 2D 扁平风格素材生成

### 温馨提示
- 当前算力资源紧张，如果出现长时间等待，或结果出现“白膜”，请耐心等待或联系支持
- 因需通过 prompt 和图片的多步合规检测，全流程大约在 4min 左右
- 一次会生成 4 张图片，如有空缺，通常是合规流程拦截导致
- 如有任何建议和问题，请在右下角留言，感谢你的支持

*祝你日日开心，出图顺利！*
  `,
    duration: 100000,
    version: "1.0.1",
    alwaysShow: true,
}

const NOTICE_API = '/api/notice'

const normalizeNoticeConfig = (payload: unknown): NoticeConfig => {
    if (!payload || typeof payload !== 'object') {
        return NOTICE_CONFIG
    }

    const source = payload as Partial<NoticeConfig>

    return {
        title: typeof source.title === 'string' && source.title.trim() ? source.title.trim() : NOTICE_CONFIG.title,
        content: typeof source.content === 'string' && source.content.trim() ? source.content : NOTICE_CONFIG.content,
        duration: typeof source.duration === 'number'
            ? Math.max(1000, Math.min(Math.floor(source.duration), 3600000))
            : NOTICE_CONFIG.duration,
        version: typeof source.version === 'string' && source.version.trim() ? source.version.trim() : NOTICE_CONFIG.version,
        alwaysShow: typeof source.alwaysShow === 'boolean' ? source.alwaysShow : NOTICE_CONFIG.alwaysShow,
    }
}

export const fetchNoticeConfig = async (): Promise<NoticeConfig> => {
    try {
        const response = await fetch(`${NOTICE_API}?_t=${Date.now()}`, {
            method: 'GET',
            cache: 'no-store',
            headers: {
                'Cache-Control': 'no-cache',
                Pragma: 'no-cache',
            },
        })

        if (!response.ok) {
            throw new Error(`公告接口请求失败: ${response.status}`)
        }

        const json = await response.json()
        const payload = (
            json &&
            typeof json === 'object' &&
            'data' in json &&
            (json as { data?: unknown }).data !== undefined
        )
            ? (json as { data: unknown }).data
            : json

        return normalizeNoticeConfig(payload)
    } catch (error) {
        console.warn('加载远程公告失败，使用本地配置:', error)
        return NOTICE_CONFIG
    }
}
