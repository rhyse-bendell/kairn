class AdapterRegistry:
    def __init__(self): self.adapters=[]
    def register(self,a): self.adapters.append(a)
    def resolve(self,c):
        scored=[(a.can_handle(c),a) for a in self.adapters]
        return [a for s,a in sorted(scored,key=lambda x:x[0], reverse=True) if s>0]
