"""Bounded extension of the verified English quest-row GUI; never changes its atlas."""
import hashlib
import struct

SOURCE_SHA = "95730f3adbaf2c017968cb0079a0caa666de541cecd66ff8ad223e1137b30c5a"
TEXTURE_HASH = 459477923
BADGE_ID = 21
BADGE_SLOT = 12

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
            if kind in (3,17,18):
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

def extend(data):
    """Append relocated tables/values; preserve original buffers, names and unknown bytes."""
    require(hashlib.sha256(data).hexdigest()==SOURCE_SHA, "Unsupported counter.gui; merge/research its changes first")
    g = Gui(data)
    animations = g.table(40,164,24); objects = g.table(48,172,36)
    sequences = g.table(52,176,16); init = g.table(56,180,20)
    require(g.word(68)==63 and g.word(48)==56, "Unexpected native row layout")
    row_index = next(i for i,a in enumerate(animations) if struct.unpack_from("<I",a)[0]==20)
    row = bytearray(animations[row_index]); count, seq_count, drawn = struct.unpack_from("<hhh",row,4)
    root = struct.unpack_from("<I",row,12)[0]
    require((root,count,seq_count,drawn)==(30,12,15,9), "Unexpected row animation")
    require(g.word(g.word(232)+6*64)==22, "Missing existing lobby atlas reference")
    require(g.text(g.word(g.word(232)+6*64+44))=="eng\\GUI\\99_texture\\HD_lobby00_BM_NOMIP", "Wrong native atlas")
    # Standard cGUIObjTexture has no cached TextureSet geometry. Preserve the
    # original vertex buffer verbatim; rGUI::setData copies that exact byte span.
    out = bytearray(data)
    def append(blob):
        out.extend(b"\0"*((-len(out))%16)); at=len(out); out.extend(blob); return at
    name_offset = append(b"QuestBadge\0")-g.word(260)
    template = bytearray(objects[32]); old_first = struct.unpack_from("<I",template,24)[0]
    new_first = len(init)
    replacements = {"PosX":(-28.0,),"PosY":(8.0,),"Size":(24.,24.,0.,0.),
                    "Texture":(22,),"Visible":(0,),"VertexColor":(128.,128.,128.,255.),
                    "mTextureRect":(136.,344.,198.,406.)}
    for raw in init[old_first:old_first+template[4]]:
        item = bytearray(raw); prop = g.text(struct.unpack_from("<I",item,12)[0]); kind=item[4]
        if prop in replacements:
            values=replacements[prop]
            fmt, section = ("<B",268) if kind in (3,17,18) else ("<4f",276) if kind==4 else ("<f",272) if kind==2 else ("<I",272)
            value_offset=append(struct.pack(fmt,*values))-g.word(section)
            struct.pack_into("<I",item,16,value_offset)
        init.append(bytes(item))
    # Link the badge as a sibling of Null_ticket under the row's main Null.
    # Appending after Tex_img would instead inherit the ticket's local offset.
    parent_tail = bytearray(objects[39]); require(struct.unpack_from("<i",parent_tail,8)[0]==-1, "Unexpected row sibling chain")
    struct.pack_into("<i",parent_tail,8,42); objects[39]=bytes(parent_tail)
    struct.pack_into("<I",template,0,BADGE_ID)
    struct.pack_into("<ii",template,8,-1,-1)
    struct.pack_into("<I",template,16,name_offset)
    struct.pack_into("<IIi",template,24,new_first,len(sequences),-1)
    template[5]=0 # No animated parameters; the native post-call updates color/visibility.
    # An empty sequence record keeps the hidden initializer for every row state.
    sequences.extend(struct.pack("<HBBhhII",0,0,0,-1,0,0,0) for _ in range(seq_count))
    objects.insert(42,bytes(template))
    for i,raw in enumerate(objects):
        if i==42: continue
        obj=bytearray(raw)
        for at in (8,12):
            index=struct.unpack_from("<i",obj,at)[0]
            if index>=42 and not (i==39 and at==8):struct.pack_into("<i",obj,at,index+1)
        objects[i]=bytes(obj)
    struct.pack_into("<h",row,4,count+1);struct.pack_into("<h",row,8,drawn+1);animations[row_index]=bytes(row)
    for i,raw in enumerate(animations):
        if i==row_index:continue
        a=bytearray(raw);index=struct.unpack_from("<I",a,12)[0]
        if index>=42:struct.pack_into("<I",a,12,index+1)
        animations[i]=bytes(a)
    for header_count,header_offset,records in [(40,164,animations),(48,172,objects),(52,176,sequences),(56,180,init)]:
        at=append(b"".join(records));struct.pack_into("<I",out,header_count,len(records));struct.pack_into("<I",out,header_offset,at)
    struct.pack_into("<I",out,8,len(out))
    verify(data,bytes(out))
    return bytes(out)

def verify(original, patched):
    """Check all original bindings and unaffected bytes, not just badge properties."""
    a,b=Gui(original),Gui(patched)
    require(b.word(48)==a.word(48)+1 and b.word(52)==a.word(52)+15, "Bad object/sequence counts")
    badge=b.table(48,172,36)[42];first=struct.unpack_from("<I",badge,24)[0]
    props=b.props(first,badge[4])
    require(b.text(struct.unpack_from("<I",badge,16)[0])=="QuestBadge", "Missing badge identity")
    require(props["Texture"]==22 and props["Visible"]==0 and props["Size"]==(24.,24.,0.,0.), "Bad badge initializer")
    require(props["mTextureRect"]==(136.,344.,198.,406.) and props["PosX"]==-28., "Bad badge placement/UV")
    # The old file stays byte-identical except header words for relocated tables,
    # counts and file length.
    header_changes={8,40,48,52,56,164,172,176,180}
    for i,(x,y) in enumerate(zip(original,patched[:len(original)])):
        require(x==y or (i//4)*4 in header_changes, "Unexpected baseline byte change")
    old_objects=a.table(48,172,36);new_objects=b.table(48,172,36)
    for i,raw in enumerate(old_objects):
        actual=bytearray(new_objects[i+(i>=42)]);expected=bytearray(raw)
        if i==39:struct.pack_into("<i",expected,8,42)
        for at in (8,12):
            v=struct.unpack_from("<i",raw,at)[0]
            if v>=42:struct.pack_into("<i",expected,at,v+1)
        require(actual==expected, "Original object binding changed")
    require(a.table(52,176,16)==b.table(52,176,16)[:-15], "Existing animation sequences changed")
    require(a.table(56,180,20)==b.table(56,180,20)[:a.word(56)], "Original initializer changed")
    for count,offset,stride in [(44,168,12),(60,184,24),(68,188,36),(112,232,64)]:
        require(a.table(count,offset,stride)==b.table(count,offset,stride), "Unrelated GUI table changed")

    # Every animation keeps its existing counts/bindings except the extended row.
    for old,new in zip(a.table(40,164,24),b.table(40,164,24)):
        expected=bytearray(old);root=struct.unpack_from("<I",old,12)[0]
        if struct.unpack_from("<I",old)[0]==20:
            struct.pack_into("<h",expected,4,13);struct.pack_into("<h",expected,8,10)
        elif root>=42:struct.pack_into("<I",expected,12,root+1)
        require(new==expected,"Existing animation binding changed")
