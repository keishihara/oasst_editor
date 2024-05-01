import json
import shutil
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

JST = timezone(timedelta(hours=+9), 'JST')
DATA_DIR = Path('data/')
DATA_DIR.mkdir(exist_ok=True)

DATA_SOURCE = DATA_DIR / 'curated_data_flat.jsonl'
DATA_ID_SOURCE = DATA_DIR / 'curated_data_id.jsonl'

EDITED_DATA_DIR = DATA_DIR / 'edited'
EDITED_DATA_DIR.mkdir(exist_ok=True)
EDITED_DATA_PATH = EDITED_DATA_DIR / 'edited_data_flat.json'
# backup the edited data once in an hour
timestamp = datetime.now(JST).strftime('%Y%m%d-%Hh')
EDITED_DATA_BAK_PATH = EDITED_DATA_DIR / f'edited_data_flat.json.{timestamp}.bak'


if 'df_flat' not in st.session_state:
    df_flat = pd.read_json(DATA_SOURCE, lines=True)
    st.session_state.df_flat = df_flat

if 'df_id' not in st.session_state:
    df_id = pd.read_json(DATA_ID_SOURCE, lines=True)
    df_id['_full_message_id'] = df_id.message_ids.str.join('_')
    df_id = (
        df_id
        .sort_values(by='_full_message_id')
        .reset_index(drop=True)
        .drop(columns='_full_message_id')
    )
    st.session_state.df_id = df_id

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1


def get_thread_by_message_ids(message_ids: list[str]) -> pd.DataFrame:
    thread = st.session_state.df_flat.query('message_id.isin(@message_ids)')

    if len(thread) != len(message_ids):
        msg = 'Found duplicated message_id(s) in the flat dataset.'
        raise RuntimeError(msg)

    return thread

def update_thread_based_on_audit_data(thread: pd.DataFrame) -> pd.DataFrame:
    thread = thread.copy()
    thread = thread.set_index('message_id').transpose().to_dict('dict')

    if not EDITED_DATA_PATH.is_file():
        return pd.DataFrame(thread).transpose().reset_index(names='message_id')

    latest_data = pd.read_json(EDITED_DATA_PATH).to_dict('dict')

    for message_id,v in thread.items():
        latest_vv = latest_data.get(message_id)
        if not latest_vv:
            continue
        for k in v:
            if k not in latest_vv:
                continue
            thread[message_id][k] = latest_vv[k]

    return pd.DataFrame(thread).transpose().reset_index(names='message_id')

def go_to_prev_thread() -> None:
    current_page = st.session_state.current_page
    if current_page == 1:
        st.toast("You're at the very first thread.")
    else:
        st.session_state.current_page -= 1

def go_to_next_thread() -> None:
    current_page = st.session_state.current_page
    if current_page == len(st.session_state.df_id):
        st.toast("You're at the very last thread.")
    else:
        st.session_state.current_page += 1

def go_to_thread() -> None:
    st.session_state.current_page = st.session_state.specified_thread

def update_edited_data_file(edited_df: pd.DataFrame, current_id: pd.Series) -> None:
    cols_to_export = [
        'message_id',
        'parent_id',
        'role',
        'text_ja_audited',
        'quality',
        'ready_to_export',
        'edited_time',
    ]

    if not EDITED_DATA_PATH.is_file():
        (
            edited_df[cols_to_export]
            .set_index('message_id', drop=False)
            .transpose()
            .to_json(EDITED_DATA_PATH, force_ascii=False, indent=4)
        )
        shutil.copy2(EDITED_DATA_PATH, EDITED_DATA_BAK_PATH)
        return

    current_thread = edited_df.replace(np.nan, None).replace(np.nan, None)
    current_thread['message_tree_id'] = current_id.message_tree_id
    current_thread['edited_time'] = datetime.now(UTC).isoformat()
    current_thread = current_thread.set_index('message_id').transpose().to_dict()
    # st.write(current_thread)

    if Path.stat(EDITED_DATA_PATH).st_size == 0:
        latest_data = {}
    else:
        with Path.open(EDITED_DATA_PATH) as f:
            latest_data = json.load(f)

    latest_data.update(current_thread)
    with Path.open(EDITED_DATA_PATH, 'w') as f:
        json.dump(latest_data, f, indent=4, ensure_ascii=False)

    shutil.copy2(EDITED_DATA_PATH, EDITED_DATA_BAK_PATH)

def main() -> None:
    st.set_page_config(page_title='OASST-ja Editor', layout='wide')
    st.title('OASST-ja Editor')

    with st.sidebar:
        current_page = st.session_state.current_page
        st.write(
            f'Thread No. `{current_page} / {len(st.session_state.df_id)}` '
            f'(`{current_page / len(st.session_state.df_id) * 100:.1f}%`)',
        )

        current_id = st.session_state.df_id.iloc[current_page - 1]
        st.dataframe(current_id, use_container_width=True)

        left, right = st.columns(2)
        with left:
            st.button(':arrow_backward:', on_click=go_to_prev_thread)
        with right:
            st.button(':arrow_forward:', on_click=go_to_next_thread)

        st.slider(
            'Which page do you want to go to?',
            1,
            len(st.session_state.df_id),
            current_page,
            on_change=go_to_thread,
            key='specified_thread',
        )

    st.write('## Editable Table')
    st.write('Make your modifications in the table below.')
    msg_ids = current_id.message_ids
    thread = get_thread_by_message_ids(msg_ids)

    # labels, accepted
    cols = [
        'ready_to_export',
        'message_id',
        'parent_id',
        'role',
        'text',
        'text_ja_audited',
        'quality',
        'accepted',
        'edited_time',
        'text_ja',
    ]

    column_config = {
        'ready_to_export': st.column_config.CheckboxColumn(
            'Ready to export',
            width=50,
        ),
        'message_id': st.column_config.TextColumn(
            'Message ID',
            disabled=True,
            width=1,
        ),
        'parent_id': st.column_config.TextColumn(
            'Parent ID',
            disabled=True,
            width=1,
        ),
        'role': st.column_config.TextColumn(
            'Role',
            disabled=True,
            width=1,
        ),
        'text': st.column_config.TextColumn(
            'Original text',
            disabled=True,
            width=300,
        ),
        'text_ja': st.column_config.TextColumn(
            'Text in Japanese',
            disabled=True,
        ),
        'quality': st.column_config.NumberColumn(
            'Quality',
            default=None,
            min_value=1,
            max_value=5,
        ),
        # 'rank': st.column_config.NumberColumn(
        #     'Rnak',
        #     disabled=True,
        # ),
        'accepted': st.column_config.CheckboxColumn(
            'Accepted',
            disabled=True,
        ),
        'edited_time': st.column_config.DatetimeColumn(
            'Edited time',
            disabled=True,
        ),
        'text_ja_audited': st.column_config.TextColumn(
            'Text audited',
        ),
    }

    thread = update_thread_based_on_audit_data(thread)
    data_to_display = thread[cols].copy()

    edited_df = st.data_editor(
        data_to_display,
        column_config=column_config,
        use_container_width=True,
        num_rows='dynamic',
        hide_index=True,
        key='changes',
    )

    # target = pd.DataFrame(st.session_state['changes'].get('edited_rows')).transpose()
    # target

    save = st.button('Save thread')
    if save:
        update_edited_data_file(edited_df, current_id)
        st.toast(f'Current thread is saved. (Thread ID: {current_id.thread_id})', icon='✅')

    with st.expander('See more details'):
        bar = (
            thread.labels
            .apply(lambda x: pd.DataFrame(x).set_index('name')['value'].transpose().to_dict())
            .apply(pd.Series).style.bar()
        )
        st.table(bar)

    st.write('## Thread Preview')
    preview_df = edited_df.copy()
    preview_df.text = preview_df.text.str.replace('\n', '<br>')
    preview_df.text_ja = preview_df.text_ja.str.replace('\n', '<br>')
    preview_df.text_ja_audited = preview_df.text_ja_audited.str.replace('\n', '<br>')
    highlighted_rows = np.where(preview_df['ready_to_export'],
                                'background-color: green',
                                '')
    cols_to_preview = ['role', 'text', 'text_ja_audited', 'edited_time']
    try:
        html = (
            preview_df[cols_to_preview]
            .style.apply(lambda _: highlighted_rows)
            .hide(axis='index')
            .to_html(index=False)
        )
        st.markdown(html, unsafe_allow_html=True)
    except Exception as e:
        # Depending on the thread data, we get html rendering errors
        st.error(e)

if __name__ == '__main__':
    main()
