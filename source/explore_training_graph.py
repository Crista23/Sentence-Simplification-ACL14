#!/usr/bin/env python
#===================================================================================
#title           : explore_training_graph.py                                       =
#description     : Training graph explorer                                         =
#author          : Shashi Narayan, shashi.narayan(at){ed.ac.uk,loria.fr,gmail.com})=                                    
#date            : Created in 2014, Later revised in April 2016.                   =
#version         : 0.1                                                             =
#===================================================================================


from training_graph_module import Training_Graph
import function_select_methods
import functions_prepare_elementtree_dot

class Explore_Training_Graph:
    def __init__(self, output_stream, DISCOURSE_SENTENCE_MODEL, MAX_SPLIT_PAIR_SIZE, 
                 RESTRICTED_DROP_REL, ALLOWED_DROP_MOD, METHOD_TRAINING_GRAPH):
        self.output_stream = output_stream

        self.DISCOURSE_SENTENCE_MODEL = DISCOURSE_SENTENCE_MODEL
        self.MAX_SPLIT_PAIR_SIZE = MAX_SPLIT_PAIR_SIZE
        self.RESTRICTED_DROP_REL = RESTRICTED_DROP_REL
        self.ALLOWED_DROP_MOD = ALLOWED_DROP_MOD
        self.METHOD_TRAINING_GRAPH = METHOD_TRAINING_GRAPH

        self.method_training_graph = function_select_methods.select_training_graph_method(self.METHOD_TRAINING_GRAPH)
        
    def explore_training_graph(self, sentid, main_sentence, main_sent_dict, simple_sentences, boxer_graph):
        # Start a training graph
        training_graph = Training_Graph()
        nodes_2_process = []

        # Check if Discourse information is available
        if boxer_graph.isEmpty():
            # Adding finishing major node
            nodeset = boxer_graph.get_nodeset()
            filtered_mod_pos = []
            majornode_data = ("fin", nodeset, simple_sentences, filtered_mod_pos)

            # Creating major node
            majornode_name, isNew = training_graph.create_majornode(majornode_data)
            nodes_2_process.append(majornode_name) # isNew = True
        else:
            # DRS data is available for the main sentence
            # Check to add the starting node
            nodeset = boxer_graph.get_nodeset()
            majornode_name, isNew = self.addition_major_node(main_sent_dict, simple_sentences, boxer_graph, training_graph, "split", nodeset, [], [])
            nodes_2_process.append(majornode_name) # isNew = True

            # Start expanding the training graph
            self.expand_training_graph(nodes_2_process[:], main_sent_dict, boxer_graph, training_graph)
        
        # Writing sentence element
        functions_prepare_elementtree_dot.prepare_write_sentence_element(self.output_stream, sentid, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph)

        # # Check to create visual representation
        # if int(sentid) <= 100:
        #     functions_prepare_elementtree_dot.run_visual_graph_creator(sentid, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph)

    def expand_training_graph(self, nodes_2_process, main_sent_dict, boxer_graph, training_graph):
        #print nodes_2_process
        if len(nodes_2_process) == 0:
            return 

        node_name = nodes_2_process[0]
        operreq = training_graph.get_majornode_type(node_name)
        nodeset = training_graph.get_majornode_nodeset(node_name)[:]
        simple_sentences = training_graph.get_majornode_simple_sentences(node_name)[:]
        oper_candidates = training_graph.get_majornode_oper_candidates(node_name)[:]
        processed_oper_candidates = training_graph.get_majornode_processed_oper_candidates(node_name)[:]
        filtered_postions = training_graph.get_majornode_filtered_postions(node_name)[:]

        if operreq == "split":
            split_candidate_tuples = oper_candidates
            nodes_2_process = self.process_split_node_training_graph(node_name, nodeset, simple_sentences, split_candidate_tuples, 
                                                                     nodes_2_process, main_sent_dict, boxer_graph, training_graph)

        if operreq == "drop-rel":
            relnode_candidates = oper_candidates
            processed_relnode_candidates = processed_oper_candidates 
            filtered_mod_pos = filtered_postions
            nodes_2_process = self.process_droprel_node_training_graph(node_name, nodeset, simple_sentences, relnode_candidates, processed_relnode_candidates, filtered_mod_pos,
                                                                       nodes_2_process, main_sent_dict, boxer_graph, training_graph)

        if operreq == "drop-mod":
            mod_candidates = oper_candidates
            processed_mod_pos = processed_oper_candidates 
            filtered_mod_pos = filtered_postions
            nodes_2_process = self.process_dropmod_node_training_graph(node_name, nodeset, simple_sentences, mod_candidates, processed_mod_pos, filtered_mod_pos,
                                                                       nodes_2_process, main_sent_dict, boxer_graph, training_graph)

        if operreq == "drop-ood":
            oodnode_candidates = oper_candidates
            processed_oodnode_candidates = processed_oper_candidates 
            filtered_mod_pos = filtered_postions
            nodes_2_process = self.process_dropood_node_training_graph(node_name, nodeset, simple_sentences, oodnode_candidates, processed_oodnode_candidates, filtered_mod_pos,
                                                                       nodes_2_process, main_sent_dict, boxer_graph, training_graph)

        self.expand_training_graph(nodes_2_process[1:], main_sent_dict, boxer_graph, training_graph)

    def process_split_node_training_graph(self, node_name, nodeset, simple_sentences, split_candidate_tuples, nodes_2_process, main_sent_dict, boxer_graph, training_graph):
        split_candidate_results = []
        splitAchieved = False
        for split_candidate in split_candidate_tuples:
            isValidSplit, split_results = self.method_training_graph.process_split_candidate_for_split(split_candidate, simple_sentences, main_sent_dict, boxer_graph)
            # print "split_candidate : "+str(split_candidate) + " : " + str(isValidSplit)
            split_candidate_results.append((isValidSplit, split_results))
            if isValidSplit:
                splitAchieved = True

        if splitAchieved:
            # At least one split candidate succeed
            for split_candidate, results_tuple in zip(split_candidate_tuples, split_candidate_results):
                if results_tuple[0] == True:
                    # Adding the operation node
                    not_applied_cands = [item for item in split_candidate_tuples if item is not split_candidate]
                    opernode_data = ("split", split_candidate, not_applied_cands)
                    opernode_name = training_graph.create_opernode(opernode_data)
                    training_graph.create_edge((node_name, opernode_name, split_candidate))
                    
                    # Adding children major nodes
                    for item in results_tuple[1]:
                        child_nodeset = item[1]
                        child_nodeset.sort()
                        parent_child_nodeset = item[2]
                        simple_sentence = item[3]
                        
                        # Check for adding OOD or subsequent nodes
                        child_majornode_name, isNew =  self.addition_major_node(main_sent_dict, [simple_sentence], boxer_graph, training_graph, "drop-rel", child_nodeset, [], [])
                        if isNew:
                            nodes_2_process.append(child_majornode_name)
                        training_graph.create_edge((opernode_name, child_majornode_name, parent_child_nodeset))

        else:
            # None of the split candidate succeed, adding the operation node
            not_applied_cands = [item for item in split_candidate_tuples]
            opernode_data = ("split", None, not_applied_cands)
            opernode_name = training_graph.create_opernode(opernode_data)
            training_graph.create_edge((node_name, opernode_name, None))
            
            # Check for adding drop-rel or drop-mod or fin nodes
            child_nodeset = nodeset
            child_majornode_name, isNew =  self.addition_major_node(main_sent_dict, simple_sentences, boxer_graph, training_graph, "drop-rel", child_nodeset, [], [])
            if isNew:
                nodes_2_process.append(child_majornode_name)
            training_graph.create_edge((opernode_name, child_majornode_name, None))
        
        return nodes_2_process

    def process_droprel_node_training_graph(self, node_name, nodeset, simple_sentences, relnode_set, processed_relnode, filtered_mod_pos, nodes_2_process, main_sent_dict, boxer_graph, training_graph):
        relnode_to_process = relnode_set[0]
        processed_relnode.append(relnode_to_process)

        isValidDrop = self.method_training_graph.process_rel_candidate_for_drop(relnode_to_process, filtered_mod_pos, nodeset, simple_sentences, main_sent_dict, boxer_graph)
        if isValidDrop:
            # Drop this rel node, adding the operation node
            opernode_data = ("drop-rel", relnode_to_process, "True")
            opernode_name = training_graph.create_opernode(opernode_data)
            training_graph.create_edge((node_name, opernode_name, relnode_to_process))

            # Check for adding REL or subsequent nodes, (nodeset is changed)
            child_nodeset, child_filtered_mod_pos = boxer_graph.drop_relation(nodeset, relnode_to_process, filtered_mod_pos)
            child_majornode_name, isNew =  self.addition_major_node(main_sent_dict, simple_sentences, boxer_graph, training_graph, "drop-rel", child_nodeset, processed_relnode, child_filtered_mod_pos)
            if isNew:
                nodes_2_process.append(child_majornode_name)
            training_graph.create_edge((opernode_name, child_majornode_name, "True"))
        else:
            # Dont drop this rel node, adding the operation node
            opernode_data = ("drop-rel", relnode_to_process, "False")
            opernode_name = training_graph.create_opernode(opernode_data)
            training_graph.create_edge((node_name, opernode_name, relnode_to_process))

            # Check for adding REL or subsequent nodes, (nodeset is unchanged)
            child_nodeset = nodeset
            child_filtered_mod_pos = filtered_mod_pos
            child_majornode_name, isNew =  self.addition_major_node(main_sent_dict, simple_sentences, boxer_graph, training_graph, "drop-rel", child_nodeset, processed_relnode, child_filtered_mod_pos)
            if isNew:
                nodes_2_process.append(child_majornode_name)
            training_graph.create_edge((opernode_name, child_majornode_name, "False"))

        return nodes_2_process

    def process_dropmod_node_training_graph(self, node_name, nodeset, simple_sentences, modcand_set, processed_mod_pos, filtered_mod_pos, nodes_2_process, main_sent_dict, boxer_graph, training_graph):
        modcand_to_process = modcand_set[0]
        modcand_position_to_process = modcand_to_process[0]
        processed_mod_pos.append(modcand_position_to_process)

        isValidDrop = self.method_training_graph.process_mod_candidate_for_drop(modcand_to_process, filtered_mod_pos, nodeset, simple_sentences, main_sent_dict, boxer_graph)
        if isValidDrop:
            # Drop this mod pos, adding the operation node
            opernode_data = ("drop-mod", modcand_to_process, "True")
            opernode_name = training_graph.create_opernode(opernode_data)
            training_graph.create_edge((node_name, opernode_name, modcand_to_process))

            # Check for adding mod and their subsequent nodes, (nodeset is not changed)
            child_nodeset = nodeset
            filtered_mod_pos.append(modcand_position_to_process)
            child_majornode_name, isNew =  self.addition_major_node(main_sent_dict, simple_sentences, boxer_graph, training_graph, "drop-mod", child_nodeset, processed_mod_pos, filtered_mod_pos)
            if isNew:
                nodes_2_process.append(child_majornode_name)
            training_graph.create_edge((opernode_name, child_majornode_name, "True"))
        else:
            # Dont drop this pos, adding the operation node
            opernode_data = ("drop-mod", modcand_to_process, "False")
            opernode_name = training_graph.create_opernode(opernode_data)
            training_graph.create_edge((node_name, opernode_name, modcand_to_process))

            # Check for adding mod and their subsequent nodes, (nodeset is not changed)
            child_nodeset = nodeset
            child_majornode_name, isNew =  self.addition_major_node(main_sent_dict, simple_sentences, boxer_graph, training_graph, "drop-mod", child_nodeset, processed_mod_pos, filtered_mod_pos)
            if isNew:
                nodes_2_process.append(child_majornode_name)
            training_graph.create_edge((opernode_name, child_majornode_name, "False"))
        return nodes_2_process

    def process_dropood_node_training_graph(self, node_name, nodeset, simple_sentences, oodnode_set, processed_oodnode, filtered_mod_pos, nodes_2_process, main_sent_dict, boxer_graph, training_graph):
        
        oodnode_to_process = oodnode_set[0]
        processed_oodnode.append(oodnode_to_process)

        isValidDrop = self.method_training_graph.process_ood_candidate_for_drop(oodnode_to_process, filtered_mod_pos, nodeset, simple_sentences, main_sent_dict, boxer_graph)
        if isValidDrop:
            # Drop this ood node, adding the operation node
            opernode_data = ("drop-ood", oodnode_to_process, "True")
            opernode_name = training_graph.create_opernode(opernode_data)
            training_graph.create_edge((node_name, opernode_name, oodnode_to_process))

            # Check for adding OOD or subsequent nodes, (nodeset is changed)
            child_nodeset = nodeset
            child_nodeset.remove(oodnode_to_process)
            child_majornode_name, isNew =  self.addition_major_node(main_sent_dict, simple_sentences, boxer_graph, training_graph, "drop-ood", child_nodeset, processed_oodnode, filtered_mod_pos)
            if isNew:
                nodes_2_process.append(child_majornode_name)
            training_graph.create_edge((opernode_name, child_majornode_name, "True"))
        else:
            # Dont drop this ood node, adding the operation node
            opernode_data = ("drop-ood", oodnode_to_process, "False")
            opernode_name = training_graph.create_opernode(opernode_data)
            training_graph.create_edge((node_name, opernode_name, oodnode_to_process))

            # Check for adding OOD or subsequent nodes, (nodeset is unchanged)
            child_nodeset = nodeset
            child_majornode_name, isNew =  self.addition_major_node(main_sent_dict, simple_sentences, boxer_graph, training_graph, "drop-ood", child_nodeset, processed_oodnode, filtered_mod_pos)
            if isNew:
                nodes_2_process.append(child_majornode_name)
            training_graph.create_edge((opernode_name, child_majornode_name, "False"))

        return nodes_2_process

    def addition_major_node(self, main_sent_dict, simple_sentences, boxer_graph, training_graph, opertype, nodeset, processed_candidates, extra_data):
        # node type - value
        type_val = {"split":1, "drop-rel":2, "drop-mod":3, "drop-ood":4}
        operval = type_val[opertype]

        # Checking for the addition of "split" major-node
        if operval <= type_val["split"]:
            if opertype in self.DISCOURSE_SENTENCE_MODEL:
                # Calculating Split Candidates - DRS Graph node tuples
                split_candidate_tuples = boxer_graph.extract_split_candidate_tuples(nodeset, self.MAX_SPLIT_PAIR_SIZE)
                # print "split_candidate_tuples : " + str(split_candidate_tuples)

                if len(split_candidate_tuples) != 0:
                    # Adding the major node for split
                    majornode_data = ("split", nodeset, simple_sentences, split_candidate_tuples)
                    majornode_name, isNew = training_graph.create_majornode(majornode_data)
                    return majornode_name, isNew

        if operval <= type_val["drop-rel"]:
            if opertype in self.DISCOURSE_SENTENCE_MODEL:
                # Calculate drop-rel candidates
                processed_relnode = processed_candidates if opertype == "drop-rel" else []
                filtered_mod_pos = extra_data if opertype == "drop-rel" else []
                relnode_set = boxer_graph.extract_drop_rel_candidates(nodeset, self.RESTRICTED_DROP_REL, processed_relnode)
                if len(relnode_set) != 0:
                    # Adding the major nodes for drop-rel
                    majornode_data = ("drop-rel", nodeset, simple_sentences, relnode_set, processed_relnode, filtered_mod_pos)
                    majornode_name, isNew = training_graph.create_majornode(majornode_data)
                    return majornode_name, isNew
                
        if operval <= type_val["drop-mod"]:
            if opertype in self.DISCOURSE_SENTENCE_MODEL:
                # Calculate drop-mod candidates
                processed_mod_pos = processed_candidates if opertype == "drop-mod" else []
                filtered_mod_pos = extra_data
                modcand_set = boxer_graph.extract_drop_mod_candidates(nodeset, main_sent_dict, self.ALLOWED_DROP_MOD, processed_mod_pos)
                if len(modcand_set) != 0:
                    # Adding the major nodes for drop-mod
                    majornode_data = ("drop-mod", nodeset, simple_sentences, modcand_set, processed_mod_pos, filtered_mod_pos)
                    majornode_name, isNew = training_graph.create_majornode(majornode_data)
                    return majornode_name, isNew

        if operval <= type_val["drop-ood"]:
            if opertype in self.DISCOURSE_SENTENCE_MODEL:
                # Check for drop-OOD node candidates
                processed_oodnodes = processed_candidates if opertype == "drop-ood" else []
                filtered_mod_pos = extra_data 
                oodnode_candidates = boxer_graph.extract_ood_candidates(nodeset, processed_oodnodes)
                if len(oodnode_candidates) != 0:
                    # Adding the major node for drop-ood
                    majornode_data = ("drop-ood", nodeset, simple_sentences, oodnode_candidates, processed_oodnodes, filtered_mod_pos)
                    majornode_name, isNew = training_graph.create_majornode(majornode_data)
                    return majornode_name, isNew


        # None of them matched, create "fin" node
        filtered_mod_pos = extra_data
        majornode_data = ("fin", nodeset, simple_sentences, filtered_mod_pos) 
        majornode_name, isNew = training_graph.create_majornode(majornode_data)
        return majornode_name, isNew 
