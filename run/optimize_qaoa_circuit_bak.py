# %%
from qiskit_optimization import QuadraticProgram

problem = QuadraticProgram()
problem.read_from_lp_file("../demos/qiskit_patterns/data/125node_example.lp")
print(problem.prettyprint())
# %%
hamiltonian, offset = problem.to_ising()
print(hamiltonian)
from qopt_best_practices.utils import build_max_cut_graph

ham_list = [(pauli, coeff.real) for pauli, coeff in hamiltonian.to_list()]
graph = build_max_cut_graph(ham_list)
import networkx as nx

nx.draw(graph, with_labels=True)
# %%
num_qubits = problem.get_num_binary_vars()

from qiskit.transpiler.passes.routing.commuting_2q_gate_routing import SwapStrategy

swap_strategy = SwapStrategy.from_line(range(num_qubits))
# %%
from qopt_best_practices.sat_mapping import SATMapper

sm = SATMapper()
remapped_g, sat_map, min_sat_layers = sm.remap_graph_with_sat(
    graph=graph, swap_strategy=swap_strategy
)

print("Map from old to new edges: ", sat_map)
print("Min SAT layers:", min_sat_layers)
nx.draw(remapped_g, with_labels=True)
# %%
from qopt_best_practices.utils import build_max_cut_paulis
from qiskit.quantum_info import SparsePauliOp

pauli_list = build_max_cut_paulis(remapped_g)
print(pauli_list)

# define a qiskit SparsePauliOp from the list of paulis
qaoa_hamiltonian = SparsePauliOp.from_list(pauli_list)
print(qaoa_hamiltonian)
# %%
from qopt_best_practices.swap_strategies import create_qaoa_swap_circuit

edge_coloring = {(idx, idx + 1): (idx + 1) % 2 for idx in range(qaoa_hamiltonian.num_qubits)}

qaoa_circ = create_qaoa_swap_circuit(qaoa_hamiltonian, swap_strategy, edge_coloring, qaoa_layers=1)
# %%

from qiskit_ibm_runtime.fake_provider import FakeKawasaki

backend = FakeKawasaki()
print(backend.num_qubits)
# %%
# the demo uses all qubits except two corner qubits (13 and 113)
path = sorted(set(range(127)) - {13, 113})
print(path)
# %%
from qiskit.transpiler import Layout

print(path)
print(qaoa_circ.qregs[0])
initial_layout = Layout.from_intlist(path, qaoa_circ.qregs[0])  # needs qaoa_circ

# %%
from qiskit.transpiler import CouplingMap, PassManager
from qiskit.transpiler.passes import (
    FullAncillaAllocation,
    EnlargeWithAncilla,
    ApplyLayout,
    SetLayout,
)

from qiskit import transpile

basis_gates = ["rz", "sx", "x", "ecr"]

backend_cmap = CouplingMap(backend.coupling_map)

pass_manager_post = PassManager(
    [
        SetLayout(initial_layout),
        FullAncillaAllocation(backend_cmap),
        EnlargeWithAncilla(),
        ApplyLayout(),
    ]
)

# Map to initial_layout and finally enlarge with ancilla
opt_circ = pass_manager_post.run(qaoa_circ)

# Now transpile to sx, rz, x, ecr basis
# opt_circ = transpile(opt_circ, basis_gates=basis_gates)
# %%
print(opt_circ.parameters)
# %%
opt_circ.decompose(reps=2).draw("mpl", filename="tmp.png", scale=0.5, fold=False)

# %%
phy_qubits = sorted(set(range(127)) - {13, 113})
log_phy_map = {l: p for l, p in enumerate(phy_qubits)}
phy_log_map = {p: l for l, p in log_phy_map.items()}
color = 0
edge_coloring = {}
for i, j in backend.coupling_map:
    if i not in phy_qubits or j not in phy_qubits:
        continue
    edge_coloring[phy_log_map[i], phy_log_map[j]] = color
    color = (color + 1) % 15
print(edge_coloring)
# %%
