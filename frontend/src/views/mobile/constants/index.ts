/**
 * 移动端统一常量管理
 * 包含按钮类型、尺寸、通用文字等
 */

// ==================== 按钮类型 ====================
export const ButtonTypes = {
  PRIMARY: 'primary',
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error',
  INFO: 'info',
  DEFAULT: 'default',
} as const

export type ButtonType = typeof ButtonTypes[keyof typeof ButtonTypes]

// ==================== 按钮尺寸 ====================
export const ButtonSizes = {
  TINY: 'tiny',
  SMALL: 'small',
  MEDIUM: 'medium',
  LARGE: 'large',
} as const

export type ButtonSize = typeof ButtonSizes[keyof typeof ButtonSizes]

// ==================== Tag 类型 ====================
export const TagTypes = {
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error',
  INFO: 'info',
  DEFAULT: 'default',
} as const

export type TagType = typeof TagTypes[keyof typeof TagTypes]

// ==================== 表单尺寸 ====================
export const FormSizes = {
  SMALL: 'small',
  MEDIUM: 'medium',
  LARGE: 'large',
} as const

export type FormSize = typeof FormSizes[keyof typeof FormSizes]

// ==================== 通用文字 - 操作按钮 ====================
export const ButtonText = {
  // 基础操作
  CONFIRM: '确认',
  CANCEL: '取消',
  SAVE: '保存',
  DELETE: '删除',
  ADD: '添加',
  EDIT: '编辑',
  CLOSE: '关闭',
  BACK: '返回',
  SEARCH: '搜索',
  REFRESH: '刷新',
  COPY: '复制',
  TEST: '测试',
  SUBMIT: '提交',
  RESET: '重置',
  LOGS: '日志',
  TERMINAL: '终端',
  REGENERATE: '重新生成',
  BIND: '绑定',
  REVOKE: '踢出设备',
  REVOKE_ALL: '踢出所有其他设备',
  CONFIRM_CHANGE_PASSWORD: '确认修改密码',
  START_SETUP_2FA: '开始设置 2FA',
  DISABLE_2FA: '停用双重验证 (2FA)',

  // 扩展操作
  CREATE: '创建',
  UPDATE: '更新',
  REMOVE: '移除',
  ENABLE: '启用',
  DISABLE: '禁用',
  ACTIVATE: '激活',
  DEACTIVATE: '停用',
  UPLOAD: '上传',
  DOWNLOAD: '下载',
  IMPORT: '导入',
  EXPORT: '导出',
  CLEAR: '清除',
  CLEANUP: '清理',
  SYNC: '同步',
  RUN: '运行',
  STOP: '停止',
  START: '启动',
  RESTART: '重启',
  VIEW: '查看',
  MORE: '更多',
  SETTINGS: '设置',
  FILTER: '筛选',
  SORT: '排序',
  HISTORY: '历史',
  ADD_PATH: '添加路径',

  // 确认类
  CONFIRM_DELETE: '确认删除',
  CONFIRM_REMOVE: '确认移除',
  CONFIRM_ENABLE: '确认启用',
  CONFIRM_DISABLE: '确认停用',
  CONFIRM_CLEAR: '确认清除',
  CONFIRM_CLEANUP: '确认清理',

  // 发送类
  SEND: '发送',
  SEND_TEST: '发送测试',

  // 智能分析
  SMART_ANALYZE: '智能分析',
  CANCEL_SELECT: '取消选中',

  // 规则设置
  RULES_SETTINGS: '规则设置',

  // 站点导航
  QUICK_ACCESS_SITES: '快速访问常用站点',
  CATEGORY: '分类',
  QUICK_ACTIONS: '快捷操作',
  ADD_SITE: '添加站点',
  ADD_CATEGORY: '添加分类',
  EDIT_SITE: '编辑站点',
  EDIT_CATEGORY: '编辑分类',
  NO_CATEGORY: '暂无分类',
  NO_SITES: '暂无站点',
  SITE_NAME: '站点名称',
  SITE_URL: '站点 URL',
  CATEGORY_NAME: '分类名称',
  ICON_URL: '图标 URL',
  SITE_DELETED: '站点已删除',
  CATEGORY_DELETED: '分类已删除',
  SITE_UPDATED: '站点更新成功',
  CATEGORY_UPDATED: '分类更新成功',
  SITE_ADDED: '站点添加成功',
  CATEGORY_ADDED: '分类添加成功',
  DELETE_FAILED: '删除失败',
  SAVE_FAILED: '保存失败',
  FILL_SITE_INFO: '请填写完整的站点信息',
  FILL_CATEGORY_NAME: '请填写分类名称',

  // 主机管理
  MANAGE_HOST: '管理主机',
  REFRESH_ALL: '全部刷新',
  ADD_HOST: '添加主机',
  CONNECT: '连接',
  ADD_COMMAND: '添加命令',

  // 服务器管理
  ADD_SERVER: '添加服务器',
  EDIT_SERVER: '编辑服务器',
  CONFIG: '配置',
  SAVE_API_CONFIG: '保存 API 配置',
  SAVE_PROXY_CONFIG: '保存代理配置',
  SAVE_SESSION_CONFIG: '保存会话配置',
  EXPORT_CONFIG: '导出 config.json',
  IMPORT_BACKUP: '导入备份文件',
  TEST_CONNECTION: '连通性测试',
  LOGIN_AUTH: '登录鉴权',

  // 书签管理
  ADD_BOOKMARK: '添加书签',
  AI_ANALYZE: 'AI 智能整理',
  HEALTH_CENTER: '体检中心',
  IMPORT_BOOKMARKS: '导入书签',
  EXPORT_BOOKMARKS: '导出书签',
  CLEAR_ALL_BOOKMARKS: '清空所有书签',
  CREATE_FOLDER: '新建文件夹',
  SCAN_DUPLICATES: '扫描重复项',
  START_SCAN: '开始检测',
  STOP_SCAN: '停止检测',
  MERGE: '合并',
  DELETE_ALL: '删除全部',
  BATCH_DELETE_DEAD: '批量删除失效链接',

  // Docker Compose
  CREATE_PROJECT: '新建项目',
  PULL: '拉取',
  SELECT: '选择',
  BACKUP: '备份',

  // Docker 系统
  REPAIR: '修复',
  START_EXECUTE: '开始执行',

  // Docker 维护
  EDIT_JSON: '编辑 JSON',
  SAVE_CONFIG: '保存配置',
  START_CLEANUP_IMAGES: '开始清理镜像',
  START_CLEANUP_CACHE: '开始清理缓存',
  START_CLEANUP_CONTAINERS: '开始清理容器',

  // 备份历史
  RESTORE: '恢复',

  // 备份管理
  CONFIG_BACKUP_MANAGE: '配置备份管理',
  RESTORE_LATEST_BACKUP: '一键还原最新备份',
  CLEAR_ALL_BACKUP: '清空所有备份',

  // 媒体库
  REFRESH_LIBRARY_LIST: '刷新媒体库列表',
  BACKUP_ALL_LIBRARIES: '一键备份所有媒体库',
  ADD_LIBRARY: '新增媒体库',
  CREATE_LIBRARY: '创建媒体库',

  // 任务
  REFRESH_TASK_LIST: '刷新任务列表',

  // TMDB Lab
  EXECUTE_SEARCH: '执行搜索',
  EXECUTE_FETCH: '执行抓取',
  VIEW_FULL_JSON: '查看完整 JSON',
  COPY_JSON_DATA: '复制 JSON 数据',
} as const

// ==================== 通用文字 - 状态标签 ====================
export const StatusText = {
  // 基础状态
  ENABLED: '已启用',
  DISABLED: '已禁用',
  ACTIVE: '已激活',
  INACTIVE: '未激活',
  SUCCESS: '成功',
  FAILED: '失败',
  PENDING: '待处理',
  RUNNING: '运行中',
  STOPPED: '已停止',
  NORMAL: '正常',
  ABNORMAL: '异常',

  // 用户状态
  ADMIN: '管理员',
  USER: '用户',
  HIDDEN: '隐藏',

  // 服务状态
  ONLINE: '在线',
  OFFLINE: '离线',
  CONNECTED: '已连接',
  DISCONNECTED: '未连接',
  READY: '就绪',
  NOT_READY: '未就绪',

  // 任务状态
  COMPLETED: '已完成',
  PROCESSING: '处理中',
  QUEUED: '队列中',
  CANCELLED: '已取消',

  // 其他状态
  UNKNOWN: '未知',
  INSTALLED: '已安装',
  NOT_INSTALLED: '未安装',
} as const

// ==================== Tag 文本 ====================
export const TagText = {
  SCANNED: '已记忆',
  DETECTED: '探测到',
  HOST: '宿主机',
  COPY: '个副本',
} as const

// ==================== 统计文本 ====================
export const StatText = {
  DUPLICATE_GROUPS: '重复资源组',
  SUGGESTED_DELETE: '待清理项目',
  SELECTED_ITEMS: '选中的项目',
} as const

// ==================== 通用文字 - 提示信息 ====================
export const MessageText = {
  // 成功提示
  SAVE_SUCCESS: '保存成功',
  DELETE_SUCCESS: '删除成功',
  ADD_SUCCESS: '添加成功',
  UPDATE_SUCCESS: '更新成功',
  CREATE_SUCCESS: '创建成功',
  REMOVE_SUCCESS: '移除成功',
  ENABLE_SUCCESS: '启用成功',
  DISABLE_SUCCESS: '停用成功',
  ACTIVATE_SUCCESS: '激活成功',
  COPY_SUCCESS: '复制成功',
  TEST_SUCCESS: '测试成功',
  SEND_SUCCESS: '发送成功',
  SYNC_SUCCESS: '同步成功',
  RUN_SUCCESS: '运行成功',
  CLEAR_SUCCESS: '清除成功',
  IMPORT_SUCCESS: '导入成功',
  EXPORT_SUCCESS: '导出成功',
  SETTINGS_SAVED: '设置已保存',
  PATH_ADDED: '路径已添加',
  PATH_REMOVED: '路径已移除',
  PATH_EXISTS: '路径已存在',
  PLEASE_INPUT_PATH: '请输入路径',

  // 失败提示
  SAVE_FAILED: '保存失败',
  DELETE_FAILED: '删除失败',
  ADD_FAILED: '添加失败',
  UPDATE_FAILED: '更新失败',
  CREATE_FAILED: '创建失败',
  REMOVE_FAILED: '移除失败',
  OPERATION_FAILED: '操作失败',
  TEST_FAILED: '测试失败',
  SEND_FAILED: '发送失败',
  SYNC_FAILED: '同步失败',
  RUN_FAILED: '运行失败',
  CLEAR_FAILED: '清除失败',
  IMPORT_FAILED: '导入失败',
  EXPORT_FAILED: '导出失败',
  LOAD_FAILED: '加载失败',

  // 警告提示
  DELETE_CONFIRM: '确定删除此项目？',
  DELETE_USER_CONFIRM: (name: string) => `确定删除用户 ${name}？`,
  REMOVE_CONFIRM: '确定移除此项目？',
  CLEAR_CONFIRM: '确定清除所有数据？',
  UNSAVED_CHANGES: '有未保存的更改，确定离开？',

  // 输入提示
  PLEASE_INPUT: '请输入',
  PLEASE_SELECT: '请选择',
  PLEASE_INPUT_REQUIRED: '请填写必填项',
  PLEASE_SELECT_REQUIRED: '请选择必选项',

  // 加载提示
  LOADING: '加载中...',
  SAVING: '保存中...',
  DELETING: '删除中...',
  PROCESSING: '处理中...',
  SYNCING: '同步中...',

  // 任务相关
  TASK_START_SUCCESS: '任务已启动',
  TASK_START_FAILED: '启动失败',
  TASK_STOP_WARNING: '已发送停止指令',
  TASK_STOP_FAILED: '停止失败',

  // 媒体库相关
  CONFIG_SERVER_FIRST: '请先配置 Emby 服务器',
  ENTER_LIBRARY_NAME: '请输入媒体库名称',
  CREATE_LIBRARY_SUCCESS: '媒体库创建成功',
  CREATE_LIBRARY_FAILED: '创建媒体库失败',
  REMOVE_LIBRARY_SUCCESS: '媒体库已移除',
  REMOVE_LIBRARY_FAILED: '移除媒体库失败',
  LOAD_LIBRARY_FAILED: '加载媒体库列表失败',

  // TMDB Lab
  ID_FILLED_CHECK_CONFIG: '已填入 ID，请确认配置后启动抓取',

  // 终端管理
  LOAD_HOST_FAILED: '加载主机列表失败',
  FILL_HOST_INFO: '请填写完整的主机信息',
  UPDATE_HOST_SUCCESS: '主机更新成功',
  ADD_HOST_SUCCESS: '主机添加成功',
  UPDATE_HOST_FAILED: '更新主机失败',
  ADD_HOST_FAILED: '添加主机失败',
  DELETE_HOST_SUCCESS: '主机已删除',
  DELETE_HOST_FAILED: '删除主机失败',
  TERMINAL_DESKTOP_ONLY: '终端连接功能请在桌面端使用',
  LOAD_COMMAND_FAILED: '加载命令列表失败',
  FILL_COMMAND_INFO: '请填写完整的命令信息',
  UPDATE_COMMAND_SUCCESS: '命令更新成功',
  ADD_COMMAND_SUCCESS: '命令添加成功',
  SAVE_COMMAND_FAILED: '保存命令失败',
  DELETE_COMMAND_SUCCESS: '命令已删除',
  DELETE_COMMAND_FAILED: '删除命令失败',
  COMMAND_DESKTOP_ONLY: '命令执行功能请在桌面端使用',

  // 书签管理
  FILL_BOOKMARK_INFO: '请填写完整的书签信息',
  ADD_BOOKMARK_SUCCESS: '书签添加成功',
  UPDATE_BOOKMARK_SUCCESS: '书签更新成功',
  SAVE_BOOKMARK_FAILED: '保存书签失败',
  DELETE_BOOKMARK_SUCCESS: '书签已删除',
  DELETE_BOOKMARK_FAILED: '删除书签失败',
  FILL_FOLDER_NAME: '请填写文件夹名称',
  CREATE_FOLDER_SUCCESS: '文件夹创建成功',
  CREATE_FOLDER_FAILED: '创建文件夹失败',
  DELETE_FOLDER_SUCCESS: '文件夹已删除',
  DELETE_FOLDER_FAILED: '删除文件夹失败',
  CLEAR_BOOKMARKS_SUCCESS: '所有书签已清空',
  CLEAR_BOOKMARKS_FAILED: '清空书签失败',
  IMPORT_BOOKMARKS_SUCCESS: '成功导入 {count} 个书签',
  IMPORT_BOOKMARKS_FAILED: '导入书签失败',
  AI_ANALYZE_NO_SUGGESTIONS: 'AI分析完成，暂无整理建议',
  AI_ANALYZE_FAILED: 'AI分析失败',
  APPLY_SUGGESTION_SUCCESS: '已应用整理建议',
  APPLY_SUGGESTION_FAILED: '应用建议失败',
  APPLY_ALL_SUGGESTIONS_SUCCESS: '已应用所有整理建议',
  APPLY_ALL_SUGGESTIONS_FAILED: '批量应用建议失败',
  DUPLICATES_FOUND: '发现 {count} 组重复书签',
  DEAD_LINKS_FOUND: '发现 {count} 个失效链接',
  SCAN_STOPPED: '扫描已停止',
  BATCH_DELETE_SUCCESS: '已删除 {count} 个失效书签',
  BATCH_DELETE_FAILED: '批量删除失败',
  MERGE_DUPLICATES_SUCCESS: '重复书签已合并',
  MERGE_DUPLICATES_FAILED: '合并重复书签失败',
  DELETE_GROUP_SUCCESS: '书签组已删除',
  DELETE_GROUP_FAILED: '删除书签组失败',

  // Docker Compose
  ENTER_PROJECT_NAME: '请输入项目名称',
  REMOVE_PROJECT_SUCCESS: '项目已从视图移除',
  REMOVE_PROJECT_FAILED: '移除项目失败',
  OPERATION_SUCCESS: '操作成功',
  OPERATION_ABNORMAL: '操作异常',
  REQUEST_FAILED: '请求失败',
  BACKUP_TASK_CREATED: '备份任务已创建，可前往"数据备份管理"进行详细配置',
  CREATE_BACKUP_TASK_FAILED: '创建备份任务失败',

  // Docker 系统
  SERVICE_ACTION_SUCCESS: '服务已尝试{action}',
  GET_SYSTEM_INFO_FAILED: '获取系统信息失败',
  ENV_TASK_COMPLETED: '环境任务执行完毕',
  INSTALL_FAILED: '安装失败',

  // Docker 维护
  READ_DAEMON_CONFIG_FAILED: '无法读取 Daemon 配置',
  READ_RAW_CONFIG_FAILED: '无法读取原始配置',
  CONTENT_REQUIRED: '内容不能为空',
  INVALID_JSON: '无效的 JSON 格式',
  RESTART_WARNING: '保存后将重启 Docker 服务，会导致容器短暂中断',
  MANUAL_RESTART_TIP: '配置将保存，需要手动重启 Docker 服务后才能生效',
  SERVICE_RESTART_ATTEMPTED: '服务已尝试重启',
  SELECT_CLEANUP_OPTION: '请至少选择一个清理选项',
  CLEANUP_IMAGES_WARNING: '此操作将永久删除满足条件的本地镜像',
  CLEANUP_CACHE_WARNING: '此操作将清理所有未使用的构建缓存',
  CLEANUP_CONTAINERS_WARNING: '此操作将永久删除所有处于停止状态的容器',
  IMAGE_CLEANUP_STARTED: '镜像清理任务已启动',
  CACHE_CLEANUP_STARTED: '缓存清理任务已启动',
  CONTAINER_CLEANUP_STARTED: '容器清理任务已启动',

  // Docker 主机管理
  COMPLETE_HOST_INFO: '请填写完整的主机信息',
  HOST_CONFIG_UPDATED: '主机配置已更新',
  NEW_HOST_ADDED: '新主机已添加',
  HOST_DELETED: '主机已删除',
  CONNECTION_NORMAL: '连接正常',
  CONNECTION_FAILED: '连接失败',

  // 备份历史
  LOAD_HISTORY_FAILED: '加载历史记录失败',
  START_DOWNLOAD: '开始下载',
  RESTORE_DEVELOPING: '恢复功能开发中',

  // 空状态
  EMPTY_DATA: '暂无数据',
  EMPTY_LIST: '列表为空',
  EMPTY_RESULT: '没有找到结果',
  NO_SERVERS: '暂无服务器配置',
  NO_HOSTS: '暂无主机配置',
  NO_TASKS: '暂无任务',
  NO_RULES: '暂无规则',
  NO_KEYS: '暂无密钥',
  NO_BOTS: '暂无机器人',
} as const

// ==================== 通用文字 - 空状态描述 ====================
export const EmptyText = {
  NO_DATA: '暂无数据',
  NO_HOST_CONFIG: '暂无主机配置',
  NO_QUICK_COMMAND: '暂无快速命令',
  NO_BOOKMARKS: '暂无书签',
  NO_FOLDERS: '暂无文件夹',
  NO_DUPLICATES: '暂无重复项',
  NO_DEAD_LINKS: '暂无失效链接',
  NO_PROJECTS: '暂无项目',
  CLICK_TO_START: '点击上方"执行同步"或"执行搜索"开始',
} as const

// ==================== 通用文字 - 确认文本 ====================
export const ConfirmText = {
  CONFIRM_DELETE: '确认删除',
  CANCEL: '取消',
  CONFIRM: '确认',
  CONFIRM_CREATE: '确认创建',
  CONFIRM_DELETE_PROJECT: '确认删除？',
} as const

// ==================== 通用文字 - 弹窗标题 ====================
export const ModalTitle = {
  ADD_COMMAND: '添加命令',
  EDIT_COMMAND: '编辑命令',
  ADD_BOOKMARK: '添加书签',
  EDIT_BOOKMARK: '编辑书签',
  CREATE_FOLDER: '新建文件夹',
  HEALTH_CENTER: '体检中心',
  AI_SUGGESTIONS: 'AI 智能整理建议',
  CREATE_PROJECT: '新建项目',
  EDIT_PROJECT: '编辑项目',
  REMOVE_PROJECT: '移除项目',
  CREATE_BACKUP_TASK: '创建备份任务',
  ENV_REPAIR_CONFIG: '环境修复/安装配置',
  INSTALL_RESULT: '安装结果',
  CLEANUP_RESULT: '清理结果',
  EDIT_DAEMON_JSON: '编辑 daemon.json',
  CONFIRM_SAVE: '确认保存',
  CONFIRM_CLEANUP_IMAGES: '确认清理镜像',
  CONFIRM_CLEANUP_CACHE: '确认清理构建缓存',
  CONFIRM_CLEANUP_CONTAINERS: '确认清理容器',
  HOST_MANAGE: '主机管理',
  ADD_HOST: '添加主机',
  EDIT_HOST: '编辑主机',
  ADD_SCAN_PATH: '添加扫描路径',
  EDIT_BACKUP_TASK: '编辑备份任务',
  ADD_BACKUP_TASK: '新增备份任务',
  RULES_CONFIG: '智能选中与排除规则配置',
} as const

// ==================== 通用文字 - 占位符 ====================
export const Placeholder = {
  HOST_NAME: '主机名称',
  SELECT_HOST: '选择主机',
  HOST_ADDRESS_EXAMPLE: '192.168.1.1',
  PORT: '22',
  USERNAME: 'root',
  COMMAND_NAME_EXAMPLE: '例如：查看日志',
  COMMAND_CONTENT_EXAMPLE: '例如：tail -f /var/log/syslog',
  SEARCH_BOOKMARK: '搜索书签...',
  BOOKMARK_TITLE: '书签标题',
  BOOKMARK_URL: 'https://example.com',
  FOLDER_NAME: '文件夹名称',
  SEARCH_PROJECT: '搜索项目名称或路径...',
  PROJECT_NAME_EXAMPLE: '例如: my-awesome-app',
  SELECT_ROOT_DIR: '选择存放项目的根目录',
  YAML_CONTENT: '在此输入 docker-compose.yml 内容',
  PROXY_EXAMPLE: '例如: http://192.168.1.10:7890',
  ONE_PER_LINE: '每行一个',
  PROXY_HOST_EXAMPLE: '例如: 192.168.1.10',
  PORT_PLACEHOLDER: '端口',
  NO_PROXY_EXAMPLE: '例如: localhost,127.0.0.1',
  LOG_SIZE: '例如: 100m',
  JSON_PLACEHOLDER: '{\n  \"registry-mirrors\": [\n    \"https://mirror.example.com\"\n  ]\n}',
  HOST_NAME_EXAMPLE: '例如: 生产服务器',
  SSH_HOST: '127.0.0.1',
  SSH_USER: 'root',
  SCAN_PATHS_EXAMPLE: '逗号分隔，例如: /opt/docker-compose,/root/projects',
  SCAN_PATH_EXAMPLE: '例如: /opt/docker-compose',
  TASK_NAME_EXAMPLE: '例如：数据库每日备份',
  SOURCE_PATH: '/app/data',
  DESTINATION_DIR: '/backup',
  OPTIONAL: '可选',
  CRON_EXAMPLE: '0 3 * * *',
  IGNORE_PATTERN_EXAMPLE: '例如：*.log',
  SELECT_PG_HOST: '选择已配置的 PostgreSQL 主机',
  REMOTE_PATH: '远程主机上的绝对路径',

  // 重复项清理
  DISPLAY_TITLE: '例如: 4k, 2160p, 1080p',
  VIDEO_CODEC: '例如: hevc, h265, h264, av1',
  VIDEO_RANGE: '例如: dolbyvision, hdr, sdr',
  EXCLUDE_PATHS: '每行一个关键词或路径片段 (不区分大小写)\n只要完整路径中包含该词，文件就会被保护。\n\n例如：\n2023\nFeature\n/vol1/Anime/Protected',
} as const

// ==================== 通用文字 - 表单提示 ====================
export const FormHint = {
  DISPLAY_TITLE: '(对应 DisplayTitle, 如: 4k, 1080p)',
  VIDEO_CODEC: '(对应 Codec, 如: hevc, h264)',
  VIDEO_RANGE: '(对应 VideoRange, 如: hdr, sdr)',
} as const

// ==================== 通用文字 - Tab 标签 ====================
export const TabText = {
  DUPLICATE_CHECK: '重复项检测',
  DEAD_LINK_CHECK: '死链检测',
} as const

// ==================== 通用文字 - 卡片标题 ====================
export const CardTitle = {
  ENV_CHECK: '环境检测',
  DAEMON_CONFIG: 'Docker Daemon 配置',
  IMAGE_CLEANUP: '镜像清理',
  CACHE_CLEANUP: '构建缓存清理',
  CONTAINER_CLEANUP: '容器清理',
  EXECUTION_HISTORY: '执行历史',
} as const

// ==================== 通用文字 - 标签 ====================
export const Label = {
  DOCKER_VERSION: 'Docker 版本',
  COMPOSE_VERSION: 'Compose 版本',
  SERVICE_STATUS: '服务状态',
  OS: '操作系统',
  HISTORY_RECORD: '历史记录',
  LEVEL: '等级',
  AUTO_SCHEDULE: '自动化运行计划',
  COMMON_PRESETS: '常用预设',
  SELECT_HOST_FIRST: '请先选择主机',
  LOADING_DATABASES: '正在加载数据库列表...',
  BACKUP_HISTORY: '备份历史',
  SELECT_PATH: '选择路径',
  CURRENT_PATH: '当前路径',
  GO_UP: '返回上级',
  GO_HOME: '返回首页',
  SIZE: '大小',
  MESSAGE: '消息',
} as const

// ==================== 通用文字 - 提示文本 ====================
export const AlertText = {
  ENV_CHECK_TIP: '本页面显示的是远程 Docker 主机的实时环境状态。如果 Docker 或 Compose 未安装，您可以使用"修复"功能尝试自动安装。',
  REPAIR_WARNING: '此操作将修改远程主机的系统组件。如果主机已有 Docker 运行，执行此操作可能会尝试更新或重置配置。',
  DAEMON_CONFIG_TIP: '该配置将直接修改远程主机的 /etc/docker/daemon.json 文件',
  PROXY_ONLY_HTTP: '仅支持 HTTP/HTTPS 协议代理',
  IMAGE_CLEANUP_TIP: '清理无用的 Docker 镜像以释放磁盘空间',
  CACHE_CLEANUP_TIP: '清理 Docker Buildx 或 BuildKit 的构建缓存',
  CONTAINER_CLEANUP_TIP: '清理所有处于停止状态的 Docker 容器',
  EDIT_JSON_WARNING: '警告：直接编辑 JSON 可能会导致 Docker 无法启动',
} as const

// ==================== 通用文字 - 页面标题 ====================
export const PageTitle = {
  // 系统页面
  HOME: '首页',
  TOOLS: '工具',
  PROFILE: '我的',
  SETTINGS: '系统设置',
  SEARCH: '搜索',
  ABOUT: '关于',

  // 工具页面
  DOCKER_MANAGER: 'Docker 管理',
  POSTGRES_MANAGER: 'PostgreSQL 管理',
  BACKUP_MANAGER: '备份管理',
  EMBY_TOOLS: 'Emby 工具',
  IMAGE_BUILDER: '镜像构建',
  TERMINAL: '终端',
  SITE_NAV: '站点导航',
  NOTIFICATIONS: '通知中心',

  // 设置页面
  SERVER_SETTINGS: '服务器设置',
  API_SETTINGS: 'API 配置',
  APPEARANCE_SETTINGS: '外观设置',
  SYSTEM_INFO: '系统信息',
  DATA_MANAGEMENT: '数据管理',
  ACCOUNT_SETTINGS: '账号设置',
} as const

// ==================== 通用文字 - 表单标签 ====================
export const FormLabel = {
  // 基础字段
  NAME: '名称',
  DESCRIPTION: '描述',
  URL: '地址',
  PATH: '路径',
  TYPE: '类型',
  STATUS: '状态',
  CREATED_AT: '创建时间',
  UPDATED_AT: '更新时间',

  // 服务器相关
  SERVER_NAME: '服务器名称',
  SERVER_URL: '服务器地址',
  API_KEY: 'API 密钥',

  // 用户相关
  USERNAME: '用户名',
  PASSWORD: '密码',
  CONFIRM_PASSWORD: '确认密码',
  EMAIL: '邮箱',
  ROLE: '角色',

  // 配置相关
  THEME: '主题模式',
  LANGUAGE: '语言',
  ENABLED: '是否启用',

  // Docker 相关
  CONTAINER_NAME: '容器名称',
  IMAGE_NAME: '镜像名称',
  HOST: '主机',
  PORT: '端口',

  // 终端管理
  HOST_ADDRESS: '主机地址',
  AUTH_TYPE: '认证方式',
  COMMAND_NAME: '命令名称',
  COMMAND_CONTENT: '命令内容',

  // 书签管理
  TITLE: '标题',
  FOLDER: '文件夹',
  FOLDER_NAME: '文件夹名称',

  // Docker Compose
  PROJECT_NAME: '项目名称',
  BASE_SAVE_PATH: '基础保存路径',
  FULL_SAVE_PATH: '完整保存路径',
  YAML_CONTENT: 'YAML 内容',

  // Docker 系统
  USE_MIRROR: '使用国内镜像',
  PROXY: '安装代理',

  // Docker 维护
  MIRROR_ACCELERATOR: '镜像加速器',
  PRIVATE_REGISTRY: '私有仓库 (insecure-registries)',
  PROXY_SETTINGS: '代理设置',
  SERVER_ADDRESS: '服务器地址',
  NO_PROXY_ADDRESSES: '不代理的地址',
  LOG_SIZE: '日志大小',
  LOG_FILES: '日志文件数',
  ENABLE_LIVE_RESTORE: '启用 live-restore',
  RESTART_AFTER_SAVE: '保存后重启服务',
  CLEAN_UNTAGGED_IMAGES: '清理无标签镜像',
  CLEAN_ALL_UNUSED_IMAGES: '清理所有未使用镜像',

  // Docker 主机管理
  SSH_ADDRESS: 'SSH 地址',
  SSH_PORT: 'SSH 端口',
  SSH_USER: 'SSH 用户',
  SSH_PASSWORD: 'SSH 密码',
  HOST_MARK: '宿主机标记',
  HOST_MARK_TIP: '标记为此 Lens 容器所在的物理宿主机',
  SCAN_PATHS: '扫描路径',
  SCAN_PATH: '扫描路径',

  // 重复项清理
  DISPLAY_TITLE: '媒体规格',
  VIDEO_CODEC: '视频编码',
  VIDEO_RANGE: '动态范围',
  TIE_BREAKER: '平局决策',
  EXCLUDE_PATHS: '白名单排除',

  // 备份任务
  TASK_NAME: '任务名称',
  BACKUP_MODE: '备份模式',
  STORAGE_MEDIUM: '存储介质',
  SYNC_STRATEGY: '同步策略',
  SOURCE_PATH: '源路径',
  DESTINATION_DIR: '目标目录',
  COMPRESSION_LEVEL: '压缩强度',
  ENCRYPTION_PASSWORD: '加密密码',
  ENABLE_SCHEDULE: '启用定时备份',
  RUN_FREQUENCY: '运行频率',
  EXECUTION_TIME: '执行时间',
  INTERVAL_TIME: '间隔时间',
  CRON_EXPRESSION: 'Cron 表达式',
  IGNORE_PATTERN: '忽略模式',
  PG_HOST: 'PG 主机',
  PG_DATABASES: '待备份数据库',
} as const

// ==================== 主题选项 ====================
export const ThemeOptions = [
  { label: '浅色', value: 'light' },
  { label: '深色', value: 'dark' },
  { label: '自动', value: 'auto' },
] as const

// ==================== 语言选项 ====================
export const LanguageOptions = [
  { label: '简体中文', value: 'zh-CN' },
  { label: 'English', value: 'en-US' },
] as const

// ==================== 快捷操作配置 ====================
export const QuickActions = [
  { name: '站点导航', path: '/mobile/tools/sitenav', color: '#705df2' },
  { name: '终端', path: '/mobile/tools/terminal', color: '#f59e0b' },
  { name: 'Docker', path: '/mobile/tools/docker', color: '#3b82f6' },
  { name: '重复项清理', path: '/mobile/tools/dedupe', color: '#ef4444' },
] as const

// ==================== 底部导航配置 ====================
export const BottomNavItems = [
  { name: '首页', path: '/mobile/home' },
  { name: '工具', path: '/mobile/tools' },
  { name: '我的', path: '/mobile/profile' },
] as const

// ==================== 颜色常量 ====================
export const Colors = {
  PRIMARY: '#705df2',
  SUCCESS: '#4ade80',
  WARNING: '#f59e0b',
  ERROR: '#ef4444',
  INFO: '#3b82f6',

  // 快捷功能颜色
  SITE_NAV: '#705df2',
  DASHBOARD: '#4ade80',
  TERMINAL: '#f59e0b',
  DOCKER: '#3b82f6',
} as const
