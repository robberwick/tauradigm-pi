import mahotas as mh
import networkx as nx
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
#from skimage import morphology

def branchedPoints(skel, showSE=False):
    X=[]
    #cross X
    X0 = np.array([[0, 1, 0], 
                   [1, 1, 1], 
                   [0, 1, 0]])
    X1 = np.array([[1, 0, 1], 
                   [0, 1, 0], 
                   [1, 0, 1]])
    X.append(X0)
    X.append(X1)
    #T like
    T=[]
    #T0 contains X0
    T0=np.array([[2, 1, 2], 
                 [1, 1, 1], 
                 [2, 2, 2]])
            
    T1=np.array([[1, 2, 1], 
                 [2, 1, 2],
                 [1, 2, 2]])  # contains X1
  
    T2=np.array([[2, 1, 2], 
                 [1, 1, 2],
                 [2, 1, 2]])
    
    T3=np.array([[1, 2, 2],
                 [2, 1, 2],
                 [1, 2, 1]])
    
    T4=np.array([[2, 2, 2],
                 [1, 1, 1],
                 [2, 1, 2]])
    
    T5=np.array([[2, 2, 1], 
                 [2, 1, 2],
                 [1, 2, 1]])
    
    T6=np.array([[2, 1, 2],
                 [2, 1, 1],
                 [2, 1, 2]])
    
    T7=np.array([[1, 2, 1],
                 [2, 1, 2],
                 [2, 2, 1]])
    T.append(T0)
    T.append(T1)
    T.append(T2)
    T.append(T3)
    T.append(T4)
    T.append(T5)
    T.append(T6)
    T.append(T7)
    #Y like
    Y=[]
    Y0=np.array([[1, 0, 1], 
                 [0, 1, 0], 
                 [2, 1, 2]])
    
    Y1=np.array([[0, 1, 0], 
                 [1, 1, 2], 
                 [0, 2, 1]])
    
    Y2=np.array([[1, 0, 2], 
                 [0, 1, 1], 
                 [1, 0, 2]])
    
        
    Y3=np.array([[0, 2, 1], 
                 [1, 1, 2], 
                 [0, 1, 0]])
    
    Y4=np.array([[2, 1, 2], 
                 [0, 1, 0], 
                 [1, 0, 1]])
    Y5 = np.rot90(Y3)
    Y6 = np.rot90(Y4)
    Y7 = np.rot90(Y5)
    Y.append(Y0)
    Y.append(Y1)
    Y.append(Y2)
    Y.append(Y3)
    Y.append(Y4)
    Y.append(Y5)
    Y.append(Y6)
    Y.append(Y7)
    
    bp = np.zeros(skel.shape, dtype=int)
    for x in X:
        bp = bp + mh.morph.hitmiss(skel,x)
    for y in Y:
        bp = bp + mh.morph.hitmiss(skel,y)
    for t in T:
        bp = bp + mh.morph.hitmiss(skel,t)
        
    return bp > 0

def endPoints(skel):
    endpoint1=np.array([[0, 0, 0],
                        [0, 1, 0],
                        [2, 1, 2]])
    
    endpoint2=np.array([[0, 0, 0],
                        [0, 1, 2],
                        [0, 2, 1]])
    
    endpoint3=np.array([[0, 0, 2],
                        [0, 1, 1],
                        [0, 0, 2]])
    
    endpoint4=np.array([[0, 2, 1],
                        [0, 1, 2],
                        [0, 0, 0]])
    
    endpoint5=np.array([[2, 1, 2],
                        [0, 1, 0],
                        [0, 0, 0]])
    
    endpoint6=np.array([[1, 2, 0],
                        [2, 1, 0],
                        [0, 0, 0]])
    
    endpoint7=np.array([[2, 0, 0],
                        [1, 1, 0],
                        [2, 0, 0]])
    
    endpoint8=np.array([[0, 0, 0],
                        [2, 1, 0],
                        [1, 2, 0]])
    
    ep1=mh.morph.hitmiss(skel,endpoint1)
    ep2=mh.morph.hitmiss(skel,endpoint2)
    ep3=mh.morph.hitmiss(skel,endpoint3)
    ep4=mh.morph.hitmiss(skel,endpoint4)
    ep5=mh.morph.hitmiss(skel,endpoint5)
    ep6=mh.morph.hitmiss(skel,endpoint6)
    ep7=mh.morph.hitmiss(skel,endpoint7)
    ep8=mh.morph.hitmiss(skel,endpoint8)
    ep = ep1+ep2+ep3+ep4+ep5+ep6+ep7+ep8
    return ep > 0


def edges_from_C8skel(c8skeleton):
    '''given a skeleton defined on c8 neighborhood (use mahotas),
     \ returns labeled edges
    '''
    branchedP = branchedPoints(c8skeleton, showSE = False) > 0
    endP = endPoints(c8skeleton) > 0
    edges = np.logical_not(branchedP)*c8skeleton
    label_edges,ne = mh.label(edges)
    return label_edges

def pruning(skeleton, size):
    '''remove iteratively end points "size" 
       times from the skeleton
    '''
    for i in range(0, size):
        endpoints = endPoints(skeleton)
        endpoints = np.logical_not(endpoints)
        skeleton = np.logical_and(skeleton,endpoints)
    return skeleton



maze_im=mh.imread("maze.png")

# fltering image 
gs_maze_img = maze_im[:, :, 0] 

# otsu method 
T_otsu = mh.otsu(gs_maze_img)

# image values should be greater than otsu value 
bw_maze_img = gs_maze_img > T_otsu 

skeleton = mh.thin(bw_maze_img)
skeleton_im = Image.fromarray(skeleton)
skeleton_im.save("skeleton.png", format="PNG")

#skeleton = pruning(skeleton(1))

bp = branchedPoints(skeleton>0)
l_bp,_ = mh.label(bp)

bp_im = Image.fromarray(bp)
bp_im.save("bp.png", format="PNG")
ep = endPoints(skeleton)

ep_im = Image.fromarray(ep)
ep_im.save("ep.png", format="PNG")

edges_np = edges_from_C8skel(skeleton)
edges_np *= (255//edges_np.max())
edges_im = Image.fromarray(np.uint8(edges_np), 'L')
edges_im.save("edges.png", format="PNG")
l_ep = ep * edges_np
