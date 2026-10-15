"""Read-only fixture for the native counter row and its already-loaded atlas."""
import hashlib
import struct

SOURCE_SHA = "95730f3adbaf2c017968cb0079a0caa666de541cecd66ff8ad223e1137b30c5a"
TEXTURE_HASH = 459477923

def require(ok, message):
    if not ok:
        raise ValueError(message)

class Gui:
    """Read file-relative tables and section-relative values without running native fixups."""
    def __init__(self, data):
        self.data = data
        require(len(data) >= 300 and data[:4] == b"GUI\0", "Invalid GUI header")
        require(self.word(4) == 141077 and self.word(8) == len(data), "Unsupported GUI version/size")
        for count, offset, stride in [(40,164,24),(44,168,12),(48,172,36),(52,176,16),
                                      (56,180,20),(60,184,24),(68,188,36),(112,232,64)]:
            require(self.word(offset) + self.word(count)*stride <= len(data), "GUI table outside file")
    def word(self, at):
        require(0 <= at <= len(self.data)-4, "GUI word outside file")
        return struct.unpack_from("<I", self.data, at)[0]
    def text(self, offset):
        at = self.word(260)+offset
        require(0 <= at < len(self.data), "GUI string outside file")
        end = self.data.find(b"\0", at)
        require(end >= at, "Unterminated GUI string")
        return self.data[at:end].decode("ascii")
    def table(self, count, offset, stride):
        at = self.word(offset)
        return [self.data[at+i*stride:at+(i+1)*stride] for i in range(self.word(count))]
    def props(self, first, count):
        result = {}
        for i in range(first, first+count):
            at = self.word(180)+i*20
            name = self.text(self.word(at+12)); kind = self.data[at+4]; value = self.word(at+16)
            # Native rGUI::setData fixes up section offsets for kinds 1..16,
            # but leaves immediate bool/u32 kinds 17/18 as the value itself.
            if kind in (17,18):
                result[name] = int(value & 255 != 0) if kind == 17 else value
                continue
            if kind == 3:
                pos = self.word(268)+value; size = 1; fmt = "<B"
            elif kind in (2,15):
                pos = self.word(272)+value; size = 4; fmt = "<f"
            elif kind == 4:
                pos = self.word(276)+value; size = 16; fmt = "<4f"
            else:
                pos = self.word(272)+value; size = 4; fmt = "<I"
            require(pos+size <= len(self.data), "GUI property outside file")
            values = struct.unpack_from(fmt, self.data, pos)
            result[name] = values[0] if len(values)==1 else values
        return result


def inspect(source):
    from mhgu_assets import read_arc
    _,entries=read_arc(source)
    matches=[v['data'] for k,v in entries.items() if k[0]=='eng\\GUI\\05_meeting_p\\count\\counter']
    require(len(matches)==1,'Missing or ambiguous English counter')
    data=matches[0];require(hashlib.sha256(data).hexdigest()==SOURCE_SHA,'Unsupported counter layout')
    gui=Gui(data)
    rows=[row for row in gui.table(40,164,24) if struct.unpack_from('<I',row)[0]==20]
    require(len(rows)==1 and struct.unpack_from('<hhh',rows[0],4)==(12,15,9),'Unexpected native row')
    texture=gui.table(112,232,64)[6]
    require(struct.unpack_from('<I',texture)[0]==22 and struct.unpack_from('<I',texture,12)[0]==0x02000200,'Wrong lobby texture')
    require(gui.text(struct.unpack_from('<I',texture,44)[0])=='eng\\GUI\\99_texture\\HD_lobby00_BM_NOMIP','Wrong HD atlas name')
    require(gui.word(68)==63,'Unexpected counter instance count')
    title=gui.table(48,172,36)[34]
    require(struct.unpack_from('<I',title)[0]==6 and struct.unpack_from('<I',title,20)[0]==0x2fb82eae,
            'Counter title must be cGUIObjMessage, not cGUIObjText')
    return {'status':'PASSED','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'source_gui_sha256':SOURCE_SHA,'row_animation':20,'existing_objects':12,'existing_drawables':9,
            'existing_sequences':15,'instances':63,'texture_id':22,'archive_replacements':0,
            'title_class':'cGUIObjMessage','title_type_crc':0x2fb82eae,'title_bytes':352,
            'new_atlas':False,'runtime_test':'NOT RUN'}


def inspect_theme(source, image):
    """Trace the displayed Gathering/objective colours to original UI records.

    The native category table selects sequence/binding/message, not a screenshot
    pixel. Objective instances override their shared Message template's colour.
    """
    from mhgu_assets import read_arc
    _, entries = read_arc(source)
    data = entries[('eng\\GUI\\05_meeting_p\\count\\counter_down', 0x22948394)]['data']
    source_sha = 'fdde4d1a34247b9150bd6bb7490d4e58f7a8492a616e8345b05cd8eb28d361cb'
    require(hashlib.sha256(data).hexdigest() == source_sha, 'Quest detail UI differs from audited base/HD resource')
    gui = Gui(data)
    # Main+0x6135fc gets this row through the GOT at0x183ff78. Category3 is
    # Gathering: sequence1000008, Message binding11, QuestCounter text40.
    require(struct.unpack_from('<I', image, 0x183ff78)[0] == 0x1634b88, 'Quest category table moved')
    sequence, binding, message = struct.unpack_from('<3I', image, 0x1634b88 + 3 * 12)
    require((sequence, binding, message) == (1000008, 11, 40), 'Gathering category mapping differs')
    animation = next(row for row in gui.table(40, 164, 24) if struct.unpack_from('<I', row)[0] == 32)
    first_object = struct.unpack_from('<I', animation, 12)[0]
    obj = gui.table(48, 172, 36)[first_object + binding]
    green = gui.props(struct.unpack_from('<I', obj, 24)[0], obj[4])['Color']
    require(first_object + binding == 16 and struct.unpack_from('<I', obj)[0] == 12, 'Gathering Message binding differs')
    require(green == (0.0, 99.0, 5.0, 255.0), 'Gathering native green differs')
    # GMD's bounded text tail verifies which localized label the table selects;
    # no GMD editor or general round-trip encoder is needed for this read.
    msg = entries[('eng\\GUI\\06_msg\\QuestCounter_eng', 0x242bb29a)]['data']
    text_count, _, text_size = struct.unpack_from('<3I', msg, 24)
    require(msg[:4] == b'GMD\0' and 0 < text_size <= len(msg), 'QuestCounter message bounds differ')
    texts = msg[-text_size:].split(b'\0')
    require(len(texts) == text_count + 1 and texts[-1] == b'' and texts[message] == b'Gathering', 'Native green no longer belongs to Gathering')
    red = None
    for index, name in [(14, 'Mes_content00'), (20, 'Mes_content01')]:
        row = gui.table(68, 188, 36)[index]
        require(gui.text(struct.unpack_from('<I', row, 20)[0]) == name, 'Objective instance identity differs')
        props = gui.props(struct.unpack_from('<I', row, 28)[0], struct.unpack_from('<I', row, 16)[0])
        require(props['ColorControl'] == 2 and props['Color'] == (163.0, 0.0, 0.0, 255.0), 'Objective native red differs')
        red = props['Color']
    return {'status': 'PASSED', 'source_gui_sha256': source_sha,
            'key_rgb': '006305', 'urgent_rgb': 'A30000', 'completed_rgb': '808080',
            'gathering': {'category_table': '0x1634b88', 'category': 3,
                          'animation': 32, 'sequence': sequence, 'binding': binding,
                          'object_index': 16, 'object_id': 12, 'message_index': message,
                          'rgba': green, 'value_file_offset': '0x18c50'},
            'objective': {'instance': 14, 'name': 'Mes_content00', 'rgba': red,
                          'subquest_instance': 20, 'value_file_offset': '0x19370'},
            'sampled_from_image': False, 'runtime_test': 'NOT RUN'}
