import json
import os
from datetime import datetime

from blinker import Signal

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.service.review_service import ReviewService
from biz.utils.im import im_notifier

# 定义全局事件管理器（事件信号）
event_manager = {
    "merge_request_reviewed": Signal(),
    "push_reviewed": Signal(),
}


# 定义事件处理函数
def on_merge_request_reviewed(mr_review_entity: MergeRequestReviewEntity):
    # 发送IM消息通知
    im_msg = f"""
### 🔀 {mr_review_entity.project_name}: Merge Request

#### 合并请求信息:
- **提交者:** {mr_review_entity.author}

- **源分支**: {mr_review_entity.source_branch}
- **目标分支**: {mr_review_entity.target_branch}
- **更新时间**: {mr_review_entity.updated_at}
- **提交信息:** {mr_review_entity.commit_messages}

- [查看合并详情]({mr_review_entity.url})

- **AI Review 结果:** 

{mr_review_entity.review_result}
    """
    im_notifier.send_notification(content=im_msg, msg_type='markdown', title='Merge Request Review',
                                  project_name=mr_review_entity.project_name)

    # 记录到数据库
    ReviewService().insert_mr_review_log(mr_review_entity)


def on_push_reviewed(entity: PushReviewEntity):
    # 记录到日志文件, 日报数据 TODO: 待优化
    commits_filtered = [{'message': commit['message'], 'author': commit['author'], 'timestamp': commit['timestamp']}
                        for commit in entity.commits]
    data_dir = os.getenv('REPORT_DATA_DIR', './')
    push_data_file = "push_" + datetime.now().strftime("%Y-%m-%d") + ".json"
    push_file_path = os.path.join(data_dir, push_data_file)
    with open(push_file_path, 'a', encoding='utf-8') as f:
        for commit in commits_filtered:
            f.write(json.dumps(commit, ensure_ascii=False) + "\n")

    # 发送IM消息通知
    im_msg = f"### 🚀 {entity.project_name}: Push\n\n"
    im_msg += "#### 提交记录:\n"

    for commit in entity.commits:
        message = commit.get('message', '').strip()
        author = commit.get('author', 'Unknown Author')
        timestamp = commit.get('timestamp', '')
        url = commit.get('url', '#')
        im_msg += (
            f"- **提交信息**: {message}\n"
            f"- **提交者**: {author}\n"
            f"- **时间**: {timestamp}\n"
            f"- [查看提交详情]({url})\n\n"
        )

    if entity.review_result:
        im_msg += f"#### AI Review 结果: \n {entity.review_result}\n\n"
    im_notifier.send_notification(content=im_msg, msg_type='markdown',
                                  title=f"{entity.project_name} Push Event",
                                  project_name=entity.project_name)

    # 记录到数据库
    ReviewService().insert_push_review_log(entity)


# 连接事件处理函数到事件信号
event_manager["merge_request_reviewed"].connect(on_merge_request_reviewed)
event_manager["push_reviewed"].connect(on_push_reviewed)
