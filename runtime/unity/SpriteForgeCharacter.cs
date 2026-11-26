using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Events;

// Desktop StreamingAssets or absolute paths. Baked animation, not a live rig.
public sealed class SpriteForgeCharacter : MonoBehaviour {
    [Serializable] public class Cell { public int w,h,columns; }
    [Serializable] public class Region { public int index,x,y,w,h; }
    [Serializable] public class Layer { public string id,name,category,sheet; public int z; public bool visible; }
    [Serializable] public class Manifest {
        public int version,frame_count,fps;
        public string format,character_id,animation,body_layer,sampling;
        public bool loop;
        public Cell cell,sheet;
        public float[] pivot_px;
        public Region[] frames;
        public Layer[] layers;
    }
    [Serializable] public class Choice { public string id; public bool visible; }
    [Serializable] public class Loadout { public int version=1; public string character_id; public Choice[] visibility; }
    class Part { public GameObject go; public SpriteRenderer renderer; public Texture2D texture; public Sprite[] frames; }
    public string initialManifest;
    [Min(1)] public float pixelsPerUnit=32;
    public string sortingLayerName="Default";
    public int baseSortingOrder;
    public UnityEvent clipFinished=new UnityEvent();
    Manifest clip;
    Dictionary<string,Part> parts=new Dictionary<string,Part>();
    Dictionary<string,bool> visibility=new Dictionary<string,bool>();
    float clock; int frame; bool playing;

    void Start() { if(!string.IsNullOrEmpty(initialManifest)) LoadClip(initialManifest); }
    static string Resolve(string path) { return Path.IsPathRooted(path)?path:Path.Combine(Application.streamingAssetsPath,path); }
    static void Release(Dictionary<string,Part> values) {
        foreach(var p in values.Values) {
            if(p.go!=null) { p.go.SetActive(false); Destroy(p.go); }
            if(p.frames!=null) foreach(var s in p.frames) if(s!=null) Destroy(s);
            if(p.texture!=null) Destroy(p.texture);
        }
        values.Clear();
    }
    static bool Valid(Manifest m) {
        if(m==null||m.version!=1||m.format!="spriteforge_modular_animation"||m.frame_count<1||m.frame_count>32||m.fps<1||m.fps>60||
           m.frames==null||m.frames.Length!=m.frame_count||m.layers==null||m.layers.Length<1||m.layers.Length>24||
           m.sheet==null||m.cell==null||m.pivot_px==null||m.pivot_px.Length!=2) return false;
        if(m.sheet.w<1||m.sheet.h<1||m.sheet.w>16384||m.sheet.h>16384||m.cell.w<1||m.cell.h<1) return false;
        if(float.IsNaN(m.pivot_px[0])||float.IsNaN(m.pivot_px[1])||float.IsInfinity(m.pivot_px[0])||float.IsInfinity(m.pivot_px[1])) return false;
        var ids=new HashSet<string>();
        for(int i=0;i<m.layers.Length;i++) {
            var l=m.layers[i];
            if(l==null||string.IsNullOrEmpty(l.id)||!System.Text.RegularExpressions.Regex.IsMatch(l.id,@"^layer_[0-9]{2}$")||!ids.Add(l.id)||l.sheet!="layers/"+l.id+".png"||l.z!=i) return false;
        }
        if(!ids.Contains(m.body_layer))return false;
        for(int i=0;i<m.frames.Length;i++) {
            var r=m.frames[i];
            if(r==null||r.index!=i||r.w!=m.cell.w||r.h!=m.cell.h||r.x<0||r.y<0||(long)r.x+r.w>m.sheet.w||(long)r.y+r.h>m.sheet.h)return false;
        }
        return true;
    }
    public bool LoadClip(string path,bool keepEquipment=true) {
        var next=new Dictionary<string,Part>(); var choices=new Dictionary<string,bool>();
        try {
            path=Resolve(path);
            var m=JsonUtility.FromJson<Manifest>(File.ReadAllText(path));
            if(!Valid(m))throw new Exception("Invalid manifest");
            if(keepEquipment&&clip!=null&&(string.IsNullOrEmpty(m.character_id)||m.character_id!=clip.character_id))throw new Exception("Incompatible recipe; pass false to reset.");
            if(keepEquipment&&clip!=null&&(m.layers.Length!=parts.Count||Array.Exists(m.layers,l=>!parts.ContainsKey(l.id))))throw new Exception("Incompatible layer set; export all alternatives for each clip.");
            if(pixelsPerUnit<=0)throw new Exception("Pixels per unit must be positive");
            foreach(var l in m.layers) {
                var p=new Part();next.Add(l.id,p);
                p.texture=new Texture2D(2,2,TextureFormat.RGBA32,false);
                if(!p.texture.LoadImage(File.ReadAllBytes(Path.Combine(Path.GetDirectoryName(path),l.sheet)),true)||p.texture.width!=m.sheet.w||p.texture.height!=m.sheet.h)throw new Exception("Missing/mismatched sheet "+l.sheet);
                p.texture.filterMode=m.sampling=="nearest"?FilterMode.Point:FilterMode.Bilinear;
                p.texture.wrapMode=TextureWrapMode.Clamp;
                p.frames=new Sprite[m.frame_count];
                var pivot=new Vector2(m.pivot_px[0]/m.cell.w,1f-m.pivot_px[1]/m.cell.h);
                for(int i=0;i<m.frame_count;i++) {
                    var r=m.frames[i];p.frames[i]=Sprite.Create(p.texture,new Rect(r.x,m.sheet.h-r.y-r.h,r.w,r.h),pivot,pixelsPerUnit,0,SpriteMeshType.FullRect);
                }
                p.go=new GameObject(l.id);p.go.SetActive(false);p.go.transform.SetParent(transform,false);
                p.renderer=p.go.AddComponent<SpriteRenderer>();p.renderer.sortingLayerName=sortingLayerName;p.renderer.sortingOrder=baseSortingOrder+l.z;
                bool old;choices[l.id]=l.id==m.body_layer||(keepEquipment&&visibility.TryGetValue(l.id,out old)?old:l.visible);
            }
            Release(parts);parts=next;visibility=choices;clip=m;Play();return true;
        } catch(Exception e) { Release(next);Debug.LogError("SpriteForge: "+e.Message,this);return false; }
    }
    public void Play() { if(clip==null)return;clock=0;frame=0;playing=true;Apply(); }
    public void Pause() { playing=false; }
    public void Resume() { if(clip!=null&&(clip.loop||clock<(float)clip.frame_count/clip.fps))playing=true; }
    void Update() {
        if(!playing||clip==null)return;
        clock+=Time.deltaTime;float duration=(float)clip.frame_count/clip.fps;
        if(clip.loop)clock%=duration;
        else if(clock>=duration) { clock=duration;frame=clip.frame_count-1;playing=false;Apply();clipFinished.Invoke();return; }
        frame=Mathf.Min(clip.frame_count-1,Mathf.FloorToInt(clock*clip.fps));Apply();
    }
    void Apply() {
        if(clip==null)return;
        foreach(var l in clip.layers) { var p=parts[l.id];p.renderer.sprite=p.frames[frame];p.go.SetActive(visibility[l.id]); }
    }
    public bool SetLayerVisible(string id,bool enabled) {
        if(clip==null||id==clip.body_layer||!parts.ContainsKey(id))return false;
        visibility[id]=enabled;Apply();return true;
    }
    public bool Equip(string id) {
        if(clip==null||id==clip.body_layer||!parts.ContainsKey(id))return false;
        var item=Array.Find(clip.layers,l=>l.id==id);
        foreach(var l in clip.layers)if(l.category==item.category&&l.id!=clip.body_layer)visibility[l.id]=l.id==id;
        Apply();return true;
    }
    public void UnequipCategory(string category) {
        if(clip==null)return;
        foreach(var l in clip.layers)if(l.category==category&&l.id!=clip.body_layer)visibility[l.id]=false;
        Apply();
    }
    public void ResetEquipment() { if(clip==null)return;foreach(var l in clip.layers)visibility[l.id]=l.id==clip.body_layer||l.visible;Apply(); }
    string DefaultPath() { return Path.Combine(Application.persistentDataPath,"spriteforge_loadout.json"); }
    public bool SaveLoadout(string path=null) {
        if(clip==null||string.IsNullOrEmpty(clip.character_id))return false;
        try {
            var choices=new List<Choice>();foreach(var pair in visibility)choices.Add(new Choice{id=pair.Key,visible=pair.Value});
            File.WriteAllText(path??DefaultPath(),JsonUtility.ToJson(new Loadout{character_id=clip.character_id,visibility=choices.ToArray()},true));return true;
        } catch(Exception e) { Debug.LogError(e.Message,this);return false; }
    }
    public bool LoadLoadout(string path=null) {
        if(clip==null||string.IsNullOrEmpty(clip.character_id))return false;
        try {
            var data=JsonUtility.FromJson<Loadout>(File.ReadAllText(path??DefaultPath()));
            if(data==null||data.version!=1||data.character_id!=clip.character_id||data.visibility==null)return false;
            var next=new Dictionary<string,bool>(visibility);
            foreach(var c in data.visibility)if(c!=null&&c.id!=null&&c.id!=clip.body_layer&&next.ContainsKey(c.id))next[c.id]=c.visible;
            visibility=next;Apply();return true;
        } catch(Exception e) { Debug.LogError(e.Message,this);return false; }
    }
    void OnDestroy() { Release(parts); }
}
