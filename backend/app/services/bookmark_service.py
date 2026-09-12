import json
import os
import time
import copy
import re
from typing import List, Dict, Any, Optional

BOOKMARK_FILE = "data/bookmarks.json"

DEFAULT_DATA = {
    "bookmarks": []
}

def get_data() -> Dict[str, Any]:
    if not os.path.exists(BOOKMARK_FILE):
        return copy.deepcopy(DEFAULT_DATA)
    try:
        with open(BOOKMARK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else copy.deepcopy(DEFAULT_DATA)
    except Exception:
        return copy.deepcopy(DEFAULT_DATA)

def save_data(data: Dict[str, Any]):
    os.makedirs(os.path.dirname(BOOKMARK_FILE), exist_ok=True)
    with open(BOOKMARK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def list_bookmarks(as_tree: bool = False):
    data = get_data()
    bookmarks = data.get("bookmarks", [])
    if not as_tree:
        return bookmarks
    
    item_map = {str(item["id"]): {**item, "children": []} for item in bookmarks}
    tree = []
    sorted_items = sorted(item_map.values(), key=lambda x: x.get("order", 0))
    
    for item in sorted_items:
        p_id = item.get("parent_id")
        if p_id and str(p_id) in item_map:
            item_map[str(p_id)]["children"].append(item)
        else:
            tree.append(item)
    return tree

def add_bookmark(bookmark_data: Dict[str, Any]):
    data = get_data()
    if "id" not in bookmark_data:
        bookmark_data["id"] = f"bm_{int(time.time() * 1000)}"
    data.setdefault("bookmarks", []).append(bookmark_data)
    save_data(data)
    return bookmark_data

def update_bookmark(bm_id: str, update_data: Dict[str, Any]):
    data = get_data()
    found = False
    for i, bm in enumerate(data.get("bookmarks", [])):
        if str(bm["id"]) == str(bm_id):
            data["bookmarks"][i].update(update_data)
            found = True
            break
    if found:
        save_data(data)
    return found

def delete_bookmark(bm_id: str):
    data = get_data()
    ids_to_delete = {str(bm_id)}
    while True:
        added = False
        for bm in data.get("bookmarks", []):
            bid, pid = str(bm["id"]), str(bm.get("parent_id"))
            if pid in ids_to_delete and bid not in ids_to_delete:
                ids_to_delete.add(bid)
                added = True
        if not added: break
    
    original_len = len(data["bookmarks"])
    data["bookmarks"] = [bm for bm in data["bookmarks"] if str(bm["id"]) not in ids_to_delete]
    if len(data["bookmarks"]) != original_len:
        save_data(data)
        return True
    return False

def reorder_bookmarks(ordered_ids: List[str], parent_id: Any = "KEEP_EXISTING"):
    """
    重新排序。如果 parent_id 传入具体值（包括 None），则更新这些项的父级。
    """
    data = get_data()
    # 创建一个快速索引
    bm_lookup = {str(bm["id"]): i for i, bm in enumerate(data["bookmarks"])}
    
    for idx, bmid in enumerate(ordered_ids):
        if bmid in bm_lookup:
            target_idx = bm_lookup[bmid]
            data["bookmarks"][target_idx]["order"] = idx
            if parent_id != "KEEP_EXISTING":
                data["bookmarks"][target_idx]["parent_id"] = parent_id
                
    save_data(data)
    return True

def clear_bookmarks():
    save_data({"bookmarks": []})
    return True

def export_bookmarks_to_html() -> str:
    tree = list_bookmarks(as_tree=True)
    lines = [
        '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
        '<!-- This is an automatically generated file. -->',
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        '<TITLE>Bookmarks</TITLE>',
        '<H1>Bookmarks</H1>',
        '<DL><p>'
    ]
    def traverse(items, level):
        indent = '    ' * level
        for it in items:
            if it['type'] == 'folder':
                lines.append(f'{indent}<DT><H3>{it["title"]}</H3>')
                lines.append(f'{indent}<DL><p>')
                if it.get('children'): 
                    traverse(it['children'], level + 1)
                lines.append(f'{indent}</DL><p>')
            else:
                # 处理图标：如果是本地路径，转为 Base64
                icon_val = it.get('icon', '')
                if icon_val and icon_val.startswith('/nav_icons/'):
                    import base64
                    icon_path = os.path.join("data", icon_val.lstrip('/'))
                    if os.path.exists(icon_path):
                        try:
                            with open(icon_path, "rb") as f:
                                b64_data = base64.b64encode(f.read()).decode('utf-8')
                                # 简单根据后缀判断 mime 类型
                                ext = os.path.splitext(icon_path)[1].lower()
                                mime = "image/png"
                                if ext == '.svg': mime = "image/svg+xml"
                                elif ext == '.ico': mime = "image/x-icon"
                                elif ext in ['.jpg', '.jpeg']: mime = "image/jpeg"
                                icon_val = f"data:{mime};base64,{b64_data}"
                        except Exception:
                            pass
                
                icon_attr = f' ICON="{icon_val}"' if icon_val else ''
                lines.append(f'{indent}<DT><A HREF="{it["url"]}"{icon_attr}>{it["title"]}</A>')
    
    if tree:
        traverse(tree, 1)
        
    lines.append('</DL><p>')
    return '\n'.join(lines)

def import_from_html(html_content: str):
    from html.parser import HTMLParser
    from app.utils.logger import logger
    
    logger.info(f"📂 [导入开始] 收到 HTML 内容长度: {len(html_content)} 字符")

    class BookmarkParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.bookmarks = []
            self.parent_stack = [None]
            self.current_folder_id = None
            self.now_ms = int(time.time() * 1000)
            self.count = 0
            
            # 状态标志
            self.in_h3 = False
            self.in_a = False
            self.current_title = []
            self.current_url = None
            self.current_icon = None
            
            # 防止重复
            self.existing_urls = set()

        def set_existing_urls(self, urls):
            self.existing_urls = urls

        def handle_starttag(self, tag, attrs):
            tag = tag.upper()
            if tag == 'DL':
                if self.current_folder_id:
                    self.parent_stack.append(self.current_folder_id)
                    self.current_folder_id = None 
            elif tag == 'H3':
                self.in_h3 = True
                self.current_title = []
            elif tag == 'A':
                self.in_a = True
                self.current_title = []
                self.current_url = None
                self.current_icon = None
                for k, v in attrs:
                    if k.lower() == 'href':
                        self.current_url = v
                    elif k.lower() == 'icon':
                        self.current_icon = v

        def handle_endtag(self, tag):
            tag = tag.upper()
            if tag == 'DL':
                if len(self.parent_stack) > 1:
                    self.parent_stack.pop()
            elif tag == 'H3':
                self.in_h3 = False
                title = "".join(self.current_title).strip() or "新建文件夹"
                folder_id = f"bm_fld_{self.now_ms}_{self.count}"
                self.bookmarks.append({
                    "id": folder_id,
                    "type": "folder",
                    "title": title,
                    "parent_id": self.parent_stack[-1],
                    "order": len(self.bookmarks)
                })
                self.current_folder_id = folder_id
                self.count += 1
            elif tag == 'A':
                self.in_a = False
                if self.current_url and self.current_url not in self.existing_urls:
                    title = "".join(self.current_title).strip() or self.current_url
                    self.bookmarks.append({
                        "id": f"bm_lnk_{self.now_ms}_{self.count}",
                        "type": "file",
                        "title": title,
                        "url": self.current_url,
                        "icon": self.current_icon,
                        "parent_id": self.parent_stack[-1],
                        "order": len(self.bookmarks)
                    })
                    self.count += 1

        def handle_data(self, data):
            if self.in_h3 or self.in_a:
                self.current_title.append(data)

    # 主逻辑
    data = get_data()
    data.setdefault("bookmarks", [])
    
    existing = {bm.get("url") for bm in data["bookmarks"] if bm.get("type") == "file" and bm.get("url")}
    
    parser = BookmarkParser()
    parser.set_existing_urls(existing)
    
    try:
        logger.info("📂 [导入] 开始解析 HTML 结构...")
        parser.feed(html_content)
        logger.info(f"📂 [导入] 解析完成，发现 {parser.count} 个新项目")
    except Exception as e:
        logger.error(f"❌ [导入错误] HTML 解析异常: {str(e)}")
    
    if parser.count > 0:
        data["bookmarks"].extend(parser.bookmarks)
        save_data(data)
        logger.info("📂 [导入] 数据保存成功")
        
    return parser.count

def find_duplicates() -> List[Dict[str, Any]]:
    """
    查找重复书签。返回重复组的列表。
    """
    data = get_data()
    bookmarks = data.get("bookmarks", [])
    
    url_map = {}
    # Flatten and group
    def traverse(items):
        for item in items:
            if item.get("type") == "file" and item.get("url"):
                u = item["url"].strip()
                if u not in url_map: url_map[u] = []
                url_map[u].append(item)
            # Flatten search handles parent_id logic in list_bookmarks generally, 
            # but raw data is flat list.
            # wait, get_data returns flat list. list_bookmarks(as_tree=True) returns tree.
            # checks raw list structure:
            # "bookmarks": [ {id, parent_id, ...} ]
            # So simple iteration is enough.
    
    # get_data returns the raw dict. bookmarks is a list.
    for item in bookmarks:
        if item.get("type") == "file" and item.get("url"):
            u = item["url"].strip()
            if u:
                if u not in url_map: url_map[u] = []
                url_map[u].append(item)

    duplicates = []
    for u, items in url_map.items():
        if len(items) > 1:
            duplicates.append({
                "url": u,
                "count": len(items),
                "items": items
            })
    return duplicates

import aiohttp
import asyncio

async def check_batch_health(urls: List[str]) -> Dict[str, int]:
    """
    并发检测一批 URL 的存活状态。
    返回 {url: status_code} (0 表示连接失败)
    """
    results = {}
    
    async def check_one(session, url):
        try:
            async with session.head(url, timeout=10, allow_redirects=True, ssl=False) as response:
                return url, response.status
        except Exception:
            # Try GET if HEAD fails (some servers deny HEAD)
            try:
                async with session.get(url, timeout=10, allow_redirects=True, ssl=False) as response:
                    return url, response.status
            except Exception:
                return url, 0

    async with aiohttp.ClientSession() as session:
        tasks = [check_one(session, u) for u in urls]
        res_list = await asyncio.gather(*tasks)
        for u, status in res_list:
            results[u] = status
            
    return results
