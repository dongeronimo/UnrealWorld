"""Sophia body texture: pinker knees/elbows (both sets) + redhead alt (red hair, freckles on face and chest)."""
import numpy as np, sys
from PIL import Image
S, SRC, OUT_MAIN, OUT_ALT = sys.argv[1:5]; N=4096
d=np.load(S+'/body.npz'); co=d['co']; tri=d['tri']; tuv=d['tuv']
B=dict(zip(d['bnames'], d['bpos'])); bone=lambda n: B[n]
fwd=np.array([0,-1,0.])
def ball(c,r): return np.clip(1-np.linalg.norm(co-c,axis=1)/r,0,1)**1.5
knee=np.zeros(len(co)); elbow=np.zeros(len(co))
for s in 'LR':
    knee=np.maximum(knee, ball(bone('CC_Base_%s_Calf|h'%s)+fwd*0.05+[0,0,0.005], 0.10))
    elbow=np.maximum(elbow, ball(bone('CC_Base_%s_Forearm|h'%s)-fwd*0.04, 0.085))
hair=np.clip(d['hair']*3,0,1); headw=np.clip(d['head']+d['jaw'],0,1)
eyes=np.maximum(ball(bone('CC_Base_L_Eye|h')+[0,-0.01,0.004],0.03), ball(bone('CC_Base_R_Eye|h')+[0,-0.01,0.004],0.03))
noeye=1-np.clip(eyes*2.5,0,1)
# face: nose bridge and cheeks, between the eyes and the mouth
face=np.exp(-((co[:,2]-1.385)/0.028)**2)*np.exp(-(co[:,0]/0.068)**2)*np.clip((-co[:,1]-0.035)/0.02,0,1)
face*=headw*(1-hair)*noeye
br=(bone('CC_Base_L_Breast|h')+bone('CC_Base_R_Breast|h'))/2; c0=np.array([0,0,br[2]+0.075])
chest=np.exp(-(co[:,0]/0.13)**2-((co[:,2]-c0[2])/0.06)**2)*np.clip(-co[:,1]/0.05,0,1)*(1-np.clip(headw*2,0,1))*(1-hair)
# fringe: dark hair baked onto head, neck and shoulders, away from eyes and mouth (eyeliner, lips stay)
mouth=ball(np.array([0,-0.06,1.355]),0.03)
fringe=np.clip((co[:,2]-1.20)/0.04,0,1)*noeye*(1-np.clip(mouth*3,0,1))
F=np.stack([knee,elbow,hair,face,chest,fringe],1)

P=tuv*N; P[:,:,1]=N-P[:,:,1]
M=np.zeros((N,N,F.shape[1]),np.float32)
def tri_pixels(p, pad=0.6):
    x0,y0=np.maximum(np.floor(p.min(0)).astype(int)-1,0); x1,y1=np.minimum(np.ceil(p.max(0)).astype(int)+1,N-1)
    if x1<x0 or y1<y0: return None
    xs,ys=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
    a,b,c=p; v0=b-a; v1=c-a; den=v0[0]*v1[1]-v1[0]*v0[1]
    if abs(den)<1e-9: return None
    wx=xs-a[0]; wy=ys-a[1]
    l1=(wx*v1[1]-v1[0]*wy)/den; l2=(v0[0]*wy-wx*v0[1])/den; l0=1-l1-l2
    e=-pad*np.sqrt(v0@v0+v1@v1)/abs(den)
    m=(l0>=e)&(l1>=e)&(l2>=e)
    return (slice(y0,y1+1),slice(x0,x1+1)), m, np.stack([l0,l1,l2],-1)
for t in range(len(tri)):
    r=tri_pixels(P[t])
    if r is None: continue
    sl,m,l=r
    val=np.clip(l,0,1)@F[tri[t]]; val/=1  # ok
    o=M[sl]; o[m]=np.maximum(o[m],val[m])

# --- freckles, scattered on the surface in 3D so UV stretch and seams do not distort them
rng=np.random.default_rng(7)
A3=0.5*np.linalg.norm(np.cross(co[tri[:,1]]-co[tri[:,0]], co[tri[:,2]]-co[tri[:,0]]),axis=1)
e1=P[:,1]-P[:,0]; e2=P[:,2]-P[:,0]; A2=0.5*np.abs(e1[:,0]*e2[:,1]-e1[:,1]*e2[:,0])
FR=np.zeros((N,N),np.float32)
for zone,dens in ((3,30000.),(4,14000.)):   # freckles per m^2 at mask 1
    w=F[tri,zone].mean(1)
    n=rng.poisson(A3*w*dens*1.0)
    for t in np.nonzero(n)[0]:
        if A3[t]<=0 or A2[t]<=0: continue
        px_per_m=np.sqrt(A2[t]/A3[t])
        for _ in range(n[t]):
            u,v=rng.random(2)
            if u+v>1: u,v=1-u,1-v
            b=np.array([1-u-v,u,v])
            if rng.random()>(b@F[tri[t],zone]): continue
            c=b@P[t]; rad=rng.uniform(0.0008,0.0021)*px_per_m; op=rng.uniform(0.45,0.95)
            R=int(np.ceil(rad*2))+1; cx,cy=int(c[0]),int(c[1])
            ys,xs=np.mgrid[max(cy-R,0):min(cy+R+1,N),max(cx-R,0):min(cx+R+1,N)]
            ang=rng.uniform(0,np.pi); el=rng.uniform(0.7,1.0)
            dx=xs+.5-c[0]; dy=ys+.5-c[1]
            rx=dx*np.cos(ang)+dy*np.sin(ang); ry=(-dx*np.sin(ang)+dy*np.cos(ang))/el
            blob=op*np.clip(1.3-np.sqrt(rx*rx+ry*ry)/rad,0,1)**0.8
            sl=(slice(ys[0,0],ys[-1,0]+1),slice(xs[0,0],xs[0,-1]+1))
            FR[sl]=np.maximum(FR[sl],np.clip(blob,0,1))
zone=np.maximum(M[...,3],M[...,4]); FR*=np.clip(zone*3,0,1)

src=Image.open(SRC); alpha=src.getchannel('A'); rgb=np.asarray(src.convert('RGB')).astype(np.float32)/255
lum=rgb@[0.299,0.587,0.114]
# pink knees and elbows: multiply, so the baked fishnet lines stay black
pk=np.clip(np.maximum(M[...,0],M[...,1])*1.0,0,1)[...,None]*0.85
pink=np.array([1.0,0.70,0.74])
main=rgb*(1-pk)+rgb*pink*pk
# redhead
alt=main.copy()
sat=rgb.max(-1)-rgb.min(-1)
darkneutral=np.clip((0.42-lum)/0.12,0,1)*np.clip((0.16-sat)/0.08,0,1)
hm=np.maximum(M[...,2], M[...,5]*darkneutral)
hm=np.where(M[...,2]>0.05, np.maximum(hm, darkneutral), hm)[...,None]
# black hair spans lum ~0.02..0.45: map it onto a crimson ramp, keeping strand contrast
L=np.clip(lum/0.40,0,1)[...,None]
ramp=np.array([0.10,0.008,0.012])*(1-L)**2+np.array([0.46,0.035,0.05])*2*L*(1-L)+np.array([0.74,0.22,0.20])*L**2
alt=alt*(1-hm)+ramp*hm
fr=FR[...,None]; frcol=np.array([0.70,0.46,0.33])
alt=alt*(1-fr)+alt*frcol*fr
for img,path in ((main,OUT_MAIN),(alt,OUT_ALT)):
    o=Image.fromarray((np.clip(img,0,1)*255+0.5).astype(np.uint8),'RGB'); o.putalpha(alpha); o.save(path)
    print("saved",path)
