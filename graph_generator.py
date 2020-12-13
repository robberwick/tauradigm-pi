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

def pruning(skeleton, size):
    '''remove iteratively end points "size" 
       times from the skeleton
    '''
    for i in range(0, size):
        endpoints = endPoints(skeleton)
        endpoints = np.logical_not(endpoints)
        skeleton = np.logical_and(skeleton,endpoints)
    return skeleton

def edges_from_C8skel(c8skeleton):
    #'''given a skeleton defined on c8 neighborhood (use mahotas),
    # \ returns labeled edges
    #'''
    branchedP = branchedPoints(c8skeleton, showSE = False) > 0
    endP = endPoints(c8skeleton) > 0
    edges = np.logical_not(branchedP)*c8skeleton
    label_edges,ne = mh.label(edges)
    return label_edges

def labels_in_labeledImage(labImage):
    return np.where(mh.histogram.fullhistogram(np.uint16(labImage))[:]>0)[0][1:]

def add_bp_to_graph(Graph, Bp):
    labels_BP = labels_in_labeledImage(Bp)
    #print labels_BP
    #add_bp_to_graph(Graph, labels_BP)
    nodesN = Graph.order()
    translate_Bplabel_to_Node_index={}
    for lab in labels_BP:
        pos = np.where(Bp == lab)
        #print pos
        translate_Bplabel_to_Node_index[lab] = nodesN+lab
        Graph.add_node(nodesN+lab,kind="BP",label=lab, position=pos)
    return translate_Bplabel_to_Node_index

def add_ep_to_graph(Graph, Ep):
    '''Adds end-points from labelled Ep image to a graph and
    returns a dictionnary mapping Ep labels into Node index (necessary when adding edges into the graph)
    '''
    translate_Eplabel_to_Node_index={}
    labels_EP = labels_in_labeledImage(Ep)
    #print labels_EP
    nodesN = Graph.order()
    for lab in labels_EP:
        pos = np.where(Ep == lab)
        #print pos
        translate_Eplabel_to_Node_index[lab] = nodesN+lab
        Graph.add_node(nodesN+lab,kind="EP",label=lab, position=pos)
    return translate_Eplabel_to_Node_index

def C8skeleton_to_graph(skeletonC8):
    #images processing: extraction of branchedpoints, end-points, edges
    ep = endPoints(skeletonC8)
    bp = branchedPoints(skeletonC8, showSE = False)
    ## Label branched-points
    l_bp,_ = mh.label(bp)
    ## Label the edges
    l_edges =  edges_from_C8skel(skeletonC8)
    ##Make end-points with the same label than their edge
    l_ep = ep*l_edges 
    
    ##edges between branched-points
    endpoints_labels = np.where(mh.histogram.fullhistogram(np.uint16(l_ep))[:]==1)[0]
    edges_bp = np.copy(l_edges)
    for l in endpoints_labels:
        edges_bp[np.where(edges_bp == l)]=0
    #edges between end-points and branched points
    edges_ep_to_bp = l_edges * np.logical_not(edges_bp > 0)
    
    #Building graph
    ## Add branched points first
    G=nx.Graph()
    lab_bpTonode = add_bp_to_graph(G, l_bp)
    ## Add end-points
    lab_epTonode = add_ep_to_graph(G, l_ep)
    ##Link end-points to branched-points
    ###labels of bp
    branchedpoints_labels = np.where(mh.histogram.fullhistogram(np.uint16(l_bp))[:]==1)[0]
    for lab in branchedpoints_labels:
        pos = np.where(l_bp == lab)
        row = int(pos[0])
        col = int(pos[1])
        #search label(s) of edges in image containing edges between ep and bp
        ## first get the neighborhood of the curent bp
        neigh_epbp = edges_ep_to_bp[row-1:row+1+1,col-1:col+1+1]
        labels_in_neigh = np.where(mh.histogram.fullhistogram(np.uint16(neigh_epbp))[:]!=0)[0]
        print (neigh_epbp, labels_in_neigh[1:])
        #get node(s) of attribute label= labels_in_neigh ! may be more than one, think to a  list
        for lab_ep in labels_in_neigh[1:]:
            #search for nodes f attribute label= lab_ep
            w = np.sum(l_edges==lab_ep)
            print('linking ',lab, lab_ep, ' weight ',w)
            G.add_edge(lab_bpTonode[lab],lab_epTonode[lab_ep],weight=w)#     
    ##
    ##Now try to link branched points between them
    ##
    bps_neighborhood = {}
    branchedpoints_labels = np.where(mh.histogram.fullhistogram(np.uint16(l_bp))[:]==1)[0]
    print(branchedpoints_labels)
    for lab in branchedpoints_labels:
        pos = np.where(l_bp == lab)
        row = int(pos[0])
        col = int(pos[1])
        #search label(s) of edges in image containing edges between ep and bp
        ## first get the neighborhood of the curent bp
        neigh_epbp = edges_bp[row-1:row+1+1,col-1:col+1+1]
        labels_in_neigh = np.where(mh.histogram.fullhistogram(np.uint16(neigh_epbp))[:]!=0)[0]
        bps_neighborhood[lab]=labels_in_neigh[1:].tolist()
    print(bps_neighborhood)
    
    ## Build the dictionnary of edges see (http://stackoverflow.com/questions/21375146/pythonic-inverse-dict-non-unique-mappings)
    invert_is_edges = {item: [key for key in bps_neighborhood if item in bps_neighborhood[key]] for value in bps_neighborhood.values() for item in value}
    ## Addeges to graph
    print(invert_is_edges)
    for ed in invert_is_edges.keys():
        ## first get edge size -> its weight
        w = np.sum(edges_bp==ed)
        vertex1 = invert_is_edges[ed][0]
        vertex2 = invert_is_edges[ed][1]
        #print ed,w
        G.add_edge(vertex1,vertex2,weight=w)
        
    ## This is it !!
    return G


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


graph = C8skeleton_to_graph(skeleton)

#figsize(6,6)

#subplot(222,xticks=[],yticks=[])
nx.draw(graph)
plt.savefig("Graph.png", format="PNG")